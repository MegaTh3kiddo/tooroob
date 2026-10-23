from functools import lru_cache
from typing import Generator
import duckdb

from torob.core.security import AuthContext, UserRole, get_auth_context, require_admin_or_operator
from torob.feedback.service import FeedbackService
from torob.ingestion.loader import ingest_catalog
from torob.inquiries.service import InquiryService
from torob.intelligence.engine import TorobIntelligenceEngine
from torob.routing.distance import DistanceRouter
from torob.routing.feasibility import VisitFeasibilityEngine
from torob.routing.itinerary import ItineraryPlanner
from torob.storage.db import db_manager
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository
from fastapi import Depends


def get_catalog_repo() -> CatalogRepository:
    return CatalogRepository(con=db_manager.get_duckdb())


def get_ledger_repo() -> LedgerRepository:
    return LedgerRepository(conn=db_manager.get_sqlite())


def get_ledger_repository() -> LedgerRepository:
    return get_ledger_repo()


def verify_admin_token(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    return require_admin_or_operator(auth)


@lru_cache()
def get_intelligence_engine() -> TorobIntelligenceEngine:
    return TorobIntelligenceEngine()


def get_inquiry_service() -> InquiryService:
    return InquiryService(ledger_repo=get_ledger_repo())


def get_feedback_service() -> FeedbackService:
    return FeedbackService(ledger_repo=get_ledger_repo())


def get_visit_feasibility_engine() -> VisitFeasibilityEngine:
    return VisitFeasibilityEngine()


def get_itinerary_planner() -> ItineraryPlanner:
    return ItineraryPlanner()
