"""Administrative, Operations & Policy Evaluation Endpoints."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from pydantic import BaseModel

from torob.api.dependencies import get_ledger_repository, verify_admin_token
from torob.ingestion.snapshot import SnapshotIngestionEngine
from torob.intelligence.calibration import CalibrationEvaluator
from torob.intelligence.policy_simulator import VerificationPolicySimulator
from torob.storage.repository_ledger import LedgerRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class SnapshotIngestRequest(BaseModel):
    snapshot_id: Optional[str] = None
    source_name: str = "admin_upload"
    offers: List[Dict[str, Any]]


class PolicySimulateRequest(BaseModel):
    simulation_horizon_hours: float = 336.0


@router.get("/alerts")
def list_quality_alerts(
    unresolved_only: bool = True,
    limit: int = Query(50, ge=1, le=200),
    ledger_repo: LedgerRepository = Depends(get_ledger_repository),
    _auth: None = Depends(verify_admin_token),
):
    """List internal quality and anomaly alerts."""
    return ledger_repo.get_quality_alerts(unresolved_only=unresolved_only, limit=limit)


@router.post("/alerts/{alert_id}/resolve")
def resolve_quality_alert(
    alert_id: str,
    ledger_repo: LedgerRepository = Depends(get_ledger_repository),
    _auth: None = Depends(verify_admin_token),
):
    """Mark a quality alert as resolved."""
    ledger_repo.resolve_quality_alert(alert_id)
    return {"status": "success", "alert_id": alert_id, "is_resolved": True}


@router.get("/policy/decisions")
def list_policy_decisions(
    limit: int = Query(50, ge=1, le=200),
    ledger_repo: LedgerRepository = Depends(get_ledger_repository),
    _auth: None = Depends(verify_admin_token),
):
    """Audit inquiry policy decisions and selection propensities."""
    return ledger_repo.get_policy_decisions(limit=limit)


@router.post("/policy/simulate")
def simulate_verification_policies(
    req: PolicySimulateRequest,
    _auth: None = Depends(verify_admin_token),
):
    """Run offline deterministic policy simulation comparing verification strategies."""
    sim = VerificationPolicySimulator(simulation_horizon_hours=req.simulation_horizon_hours)
    results = sim.evaluate_policies()
    return {
        "is_simulation": True,
        "horizon_hours": req.simulation_horizon_hours,
        "results": {k: v.__dict__ for k, v in results.items()},
    }


@router.post("/snapshots/ingest")
def ingest_catalog_snapshot(
    req: SnapshotIngestRequest,
    ledger_repo: LedgerRepository = Depends(get_ledger_repository),
    _auth: None = Depends(verify_admin_token),
):
    """Ingest a catalog snapshot idempotently without destroying historical observations."""
    engine = SnapshotIngestionEngine(ledger_repo=ledger_repo)
    result = engine.ingest_snapshot(
        offers_data=req.offers,
        source_name=req.source_name,
        snapshot_id=req.snapshot_id,
    )
    return {
        "status": "success",
        "snapshot_id": result.snapshot_id,
        "record_count": result.record_count,
        "new_offers": result.new_offers_count,
        "changed_prices": result.changed_prices_count,
        "unchanged_prices": result.unchanged_prices_count,
        "checksum": result.checksum,
        "warnings": result.warnings,
    }


@router.get("/calibration/evaluate")
def evaluate_calibration(
    _auth: None = Depends(verify_admin_token),
):
    """Evaluate binary calibration metrics on deterministic synthetic benchmark fixtures."""
    preds = [0.1, 0.12, 0.15, 0.35, 0.4, 0.42, 0.78, 0.81, 0.89, 0.95] * 20
    labels = [0, 0, 0, 0, 1, 0, 1, 1, 1, 1] * 20
    eval_res = CalibrationEvaluator.evaluate_binary_calibration(preds, labels, num_bins=5)
    return {
        "brier_score": eval_res.brier_score,
        "log_loss": eval_res.log_loss,
        "expected_calibration_error": eval_res.expected_calibration_error,
        "total_samples": eval_res.total_samples,
        "reliability_bins": [b.__dict__ for b in eval_res.reliability_bins],
        "is_simulation_only": True,
        "caveat": eval_res.caveat,
    }
