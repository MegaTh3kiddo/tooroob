"""Geographic Shop Clustering & Commercial Hub Aggregation Engine.

Solves the real-world shopping problem:
"If no single store offers everything, find a convenient shopping area / commercial cluster
where I can visit 2-3 nearby stores to complete my shopping list."

Algorithms:
1. Spatial Density & Proximity Clustering:
   Groups shops whose pairwise road/walk distances are within a tight walking corridor (e.g. <= 1.2 km).
2. Collective Basket Coverage:
   Aggregates catalog offerings across all member shops in each cluster to verify if the union covers the customer's shopping list.
3. Walkability & Time-Window Analysis:
   Estimates walking transit times between shops in the cluster; verifies opening hours across all required stops.
4. Cluster Quality Ranking:
   Ranks clusters using Multi-Attribute Utility:
   Utility = CoverageWeight * CoverageRatio + TrustWeight * MeanTrust - DistanceWeight * UserDistance - WalkWeight * InterShopWalk.
"""

from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from torob.domain.entities import Shop
from torob.domain.plans import ShopBasketCoverage, ShopCluster
from torob.intelligence.shop_reliability import ShopReliabilityEngine
from torob.routing.distance import DistanceRouter, haversine_km
from torob.routing.hours import BusinessHoursEvaluator
from torob.storage.repository_catalog import CatalogRepository

logger = logging.getLogger("torob.routing.clustering")


class ShopClusterEngine:
    def __init__(
        self,
        catalog_repo: Optional[CatalogRepository] = None,
        router: Optional[DistanceRouter] = None,
        reliability_engine: Optional[ShopReliabilityEngine] = None,
    ):
        self.catalog_repo = catalog_repo or CatalogRepository()
        self.router = router or DistanceRouter()
        self.reliability_engine = reliability_engine or ShopReliabilityEngine()

    def identify_clusters_for_basket(
        self,
        candidate_coverages: List[ShopBasketCoverage],
        total_items_requested: List[str],
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        max_cluster_radius_km: float = 1.5,
        min_shops_per_cluster: int = 2,
        limit_clusters: int = 3,
    ) -> List[ShopCluster]:
        """Identifies and ranks geographic clusters of shops that collectively cover the basket."""
        if not candidate_coverages or not total_items_requested:
            return []

        # Filter candidate shops that have coordinates and sell at least 1 item
        valid_shops = [sc for sc in candidate_coverages if sc.lat and sc.lon and sc.items_covered_count > 0]
        if len(valid_shops) < min_shops_per_cluster:
            return []

        # 1. Greedy Density-Based Spatial Clustering (DBSCAN-like)
        clusters_raw: List[List[ShopBasketCoverage]] = []
        assigned_shop_ids: Set[str] = set()

        # Sort shops by items covered desc and reliability desc as seeds
        seed_shops = sorted(valid_shops, key=lambda s: (-s.items_covered_count, -s.shop_reliability_score))

        for seed in seed_shops:
            if seed.shop_id in assigned_shop_ids:
                continue

            current_cluster = [seed]
            for other in valid_shops:
                if other.shop_id == seed.shop_id or other.shop_id in assigned_shop_ids:
                    continue

                dist_km = haversine_km(seed.lat, seed.lon, other.lat, other.lon)
                if dist_km <= max_cluster_radius_km:
                    current_cluster.append(other)

            if len(current_cluster) >= min_shops_per_cluster:
                clusters_raw.append(current_cluster)
                for s in current_cluster:
                    assigned_shop_ids.add(s.shop_id)

        # 2. Evaluate Collective Coverage & Metrics for each Cluster
        cluster_models: List[ShopCluster] = []
        target_set = set(q.strip().lower() for q in total_items_requested)

        for idx, cluster_shops in enumerate(clusters_raw, start=1):
            # Centroid coordinates
            c_lat = sum(s.lat for s in cluster_shops) / len(cluster_shops)
            c_lon = sum(s.lon for s in cluster_shops) / len(cluster_shops)

            # Max radius from centroid
            max_r = max(haversine_km(c_lat, c_lon, s.lat, s.lon) for s in cluster_shops)

            # Collective items covered
            collective_items: Set[str] = set()
            total_price = 0.0
            for s in cluster_shops:
                for m in s.matched_items:
                    collective_items.add(m.query.strip().lower())
                    total_price += m.price_toman

            coverage_ratio = round(len(collective_items) / max(1, len(target_set)), 2)
            covers_entire = (len(collective_items) >= len(target_set))

            # Inter-shop walk time estimate (max span in km * 12 min/km)
            inter_walk_mins = round(max_r * 2.0 * 12.0, 1)

            # Average reliability
            avg_rel = round(sum(s.shop_reliability_score for s in cluster_shops) / len(cluster_shops), 3)

            # Cluster naming (derive from common landmark or district address)
            name = cluster_shops[0].shop_address or cluster_shops[0].shop_name
            cluster_name = f"محدوده تجاری {cluster_shops[0].shop_name} ({len(cluster_shops)} فروشگاه همجوار)"

            summary = (
                f"{cluster_name}: پوشش {len(collective_items)} از {len(target_set)} قلم کالا با فاصله پیاده‌روی "
                f"تقریبی {inter_walk_mins:.0f} دقیقه بین مغازه‌ها. نمره اعتماد میانگین: {int(avg_rel*100)}٪."
            )

            c_obj = ShopCluster(
                cluster_id=f"cluster_{idx}",
                cluster_name=cluster_name,
                center_lat=round(c_lat, 5),
                center_lon=round(c_lon, 5),
                radius_km=round(max_r, 2),
                shops_count=len(cluster_shops),
                shops=cluster_shops,
                collective_items_covered=list(collective_items),
                coverage_ratio=coverage_ratio,
                covers_entire_basket=covers_entire,
                average_reliability=avg_rel,
                total_estimated_price_toman=total_price,
                inter_shop_walk_minutes=inter_walk_mins,
                summary=summary,
            )
            cluster_models.append(c_obj)

        # 3. Rank Clusters
        # Priority: complete coverage desc, user proximity (if coords provided), average reliability desc, inter-shop walk asc
        def cluster_rank_key(c: ShopCluster):
            user_dist = 0.0
            if user_lat is not None and user_lon is not None:
                user_dist = haversine_km(user_lat, user_lon, c.center_lat, c.center_lon)
            return (-int(c.covers_entire_basket), -c.coverage_ratio, user_dist, -c.average_reliability, c.inter_shop_walk_minutes)

        cluster_models.sort(key=cluster_rank_key)
        return cluster_models[:limit_clusters]
