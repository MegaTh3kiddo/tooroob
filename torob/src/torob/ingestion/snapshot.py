"""Reproducible & Idempotent Catalog Snapshot Ingestion Engine.

Ingests catalog snapshots, maintains immutable observation history in SQLite,
detects price changes vs unchanged observations, calculates observation intervals,
and updates DuckDB analytics without destroying historical records.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

import duckdb

from torob.intelligence.invalidation import InvalidationReport, invalidation_tracker
from torob.storage.db import db_manager
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.ingestion.snapshot")


@dataclass
class IngestionResult:
    snapshot_id: str
    source_name: str
    record_count: int
    new_offers_count: int
    changed_prices_count: int
    unchanged_prices_count: int
    checksum: str
    invalidation_report: Optional[InvalidationReport] = None
    warnings: List[str] = field(default_factory=list)


class SnapshotIngestionEngine:
    def __init__(
        self,
        ledger_repo: Optional[LedgerRepository] = None,
        duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None,
    ):
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.duckdb_conn = duckdb_conn or db_manager.get_duckdb()

    def ingest_snapshot(
        self,
        offers_data: List[Dict[str, Any]],
        source_name: str = "torob_crawler",
        snapshot_id: Optional[str] = None,
        observed_at: Optional[datetime] = None,
    ) -> IngestionResult:
        """Ingest a list of offer dictionaries representing a point-in-time catalog snapshot."""
        now = observed_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Generate deterministic checksum
        serialized = json.dumps(
            sorted([{k: str(v) for k, v in o.items()} for o in offers_data], key=lambda x: str(x.get("offer_id", ""))),
            sort_keys=True,
        )
        checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        snap_id = snapshot_id or f"snap_{checksum[:12]}"

        # Check if snapshot was already ingested (idempotency check)
        existing_manifest = self.ledger_repo.conn.execute(
            "SELECT * FROM snapshot_manifests WHERE snapshot_id = ?", (snap_id,)
        ).fetchone()

        if existing_manifest:
            logger.info(f"Snapshot {snap_id} already ingested. Returning idempotent result.")
            return IngestionResult(
                snapshot_id=snap_id,
                source_name=source_name,
                record_count=existing_manifest["record_count"],
                new_offers_count=0,
                changed_prices_count=0,
                unchanged_prices_count=existing_manifest["record_count"],
                checksum=checksum,
                warnings=["Snapshot already ingested; skipped duplicate observation insertion."],
            )

        # Retrieve latest observations for existing offers to detect transitions
        existing_obs_cursor = self.ledger_repo.conn.execute(
            """
            SELECT offer_id, price_toman, observed_at
            FROM offer_observations
            WHERE (offer_id, observed_at) IN (
                SELECT offer_id, MAX(observed_at)
                FROM offer_observations
                GROUP BY offer_id
            )
            """
        )
        latest_obs_map: Dict[str, Tuple[Optional[float], datetime]] = {}
        for r in existing_obs_cursor.fetchall():
            dt = datetime.fromisoformat(r["observed_at"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            latest_obs_map[r["offer_id"]] = (r["price_toman"], dt)

        observations_to_insert = []
        changed_observations = []
        new_offers_count = 0
        changed_prices_count = 0
        unchanged_prices_count = 0

        for raw_offer in offers_data:
            offer_id = str(raw_offer.get("offer_id", "")).strip()
            shop_id = str(raw_offer.get("shop_id", "")).strip()
            product_id = str(raw_offer.get("product_id", "")).strip()
            price_val = raw_offer.get("price_toman")

            try:
                price_toman = float(price_val) if price_val is not None else None
            except (ValueError, TypeError):
                price_toman = None

            obs_id = f"obs_{snap_id}_{offer_id}"

            if offer_id in latest_obs_map:
                prev_price, prev_time = latest_obs_map[offer_id]
                interval_hours = max(0.0, (now - prev_time).total_seconds() / 3600.0)

                # Check for meaningful price change
                is_changed = False
                if price_toman is not None and prev_price is not None:
                    if abs(price_toman - prev_price) > 0.01:
                        is_changed = True
                elif (price_toman is None) != (prev_price is None):
                    is_changed = True

                if is_changed:
                    changed_prices_count += 1
                else:
                    unchanged_prices_count += 1

                obs_entry = {
                    "observation_id": obs_id,
                    "snapshot_id": snap_id,
                    "offer_id": offer_id,
                    "shop_id": shop_id,
                    "product_id": product_id,
                    "price_toman": price_toman,
                    "availability_status": raw_offer.get("availability_status", "unknown"),
                    "observed_at": now.isoformat(),
                    "is_price_changed": is_changed,
                    "previous_price_toman": prev_price,
                    "observation_interval_hours": interval_hours,
                }
                observations_to_insert.append(obs_entry)
                if is_changed:
                    changed_observations.append(obs_entry)
            else:
                new_offers_count += 1
                obs_entry = {
                    "observation_id": obs_id,
                    "snapshot_id": snap_id,
                    "offer_id": offer_id,
                    "shop_id": shop_id,
                    "product_id": product_id,
                    "price_toman": price_toman,
                    "availability_status": raw_offer.get("availability_status", "unknown"),
                    "observed_at": now.isoformat(),
                    "is_price_changed": False,
                    "previous_price_toman": None,
                    "observation_interval_hours": None,
                }
                observations_to_insert.append(obs_entry)

        # Batch insert observations
        self.ledger_repo.record_offer_observations(observations_to_insert)

        # Record manifest
        self.ledger_repo.record_snapshot_manifest(
            snapshot_id=snap_id,
            source_name=source_name,
            record_count=len(offers_data),
            checksum=checksum,
            metadata={
                "new_offers": new_offers_count,
                "changed_prices": changed_prices_count,
                "unchanged_prices": unchanged_prices_count,
            },
            created_at=now,
        )

        # Targeted invalidation
        inval_report = invalidation_tracker.track_snapshot_changes(
            changed_observations, observations_to_insert
        )

        # Upsert DuckDB current offer views if table exists
        try:
            for obs in observations_to_insert:
                if obs["price_toman"] is not None:
                    self.duckdb_conn.execute(
                        """
                        UPDATE offers
                        SET price_toman = ?, last_price_changed_at = CASE WHEN ? = 1 THEN ? ELSE last_price_changed_at END
                        WHERE offer_id = ?
                        """,
                        (
                            obs["price_toman"],
                            1 if obs["is_price_changed"] else 0,
                            now.isoformat(),
                            obs["offer_id"],
                        ),
                    )
        except Exception as e:
            logger.warning(f"Could not update DuckDB current offers directly: {e}")

        logger.info(
            f"Ingested snapshot {snap_id}: {len(offers_data)} total, {new_offers_count} new, "
            f"{changed_prices_count} changed, {unchanged_prices_count} unchanged."
        )

        return IngestionResult(
            snapshot_id=snap_id,
            source_name=source_name,
            record_count=len(offers_data),
            new_offers_count=new_offers_count,
            changed_prices_count=changed_prices_count,
            unchanged_prices_count=unchanged_prices_count,
            checksum=checksum,
            invalidation_report=inval_report,
        )
