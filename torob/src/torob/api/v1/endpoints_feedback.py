from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException

from torob.api.dependencies import get_feedback_service
from torob.api.v1.schemas import (
    ResolveCaseRequest,
    SubmitFeedbackRequest,
    SubmitSellerCaseResponseRequest,
)
from torob.core.security import (
    AuthContext,
    get_auth_context,
    require_admin_or_operator,
    verify_seller_ownership,
)
from torob.domain.entities import FeedbackCase
from torob.feedback.service import FeedbackService

router = APIRouter(tags=["Customer Feedback & Disputes"])


@router.post("/feedback", response_model=FeedbackCase, status_code=201)
def submit_customer_report(
    body: SubmitFeedbackRequest,
    auth: AuthContext = Depends(get_auth_context),
    feedback_svc: FeedbackService = Depends(get_feedback_service),
):
    """Submit customer visit report (e.g. wrong price, closed shop, wrong model, or successful purchase)."""
    reporter = body.reporter_token or auth.user_id
    return feedback_svc.submit_customer_feedback(
        shop_id=body.shop_id,
        issue_type=body.issue_type,
        offer_id=body.offer_id,
        product_id=body.product_id,
        reporter_token=reporter,
        notes=body.notes,
    )


@router.get("/feedback/cases/{case_id}")
def get_case_details(
    case_id: str,
    feedback_svc: FeedbackService = Depends(get_feedback_service),
):
    """Retrieve feedback case details, audit timeline, and events."""
    try:
        return feedback_svc.get_case_with_history(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/feedback/cases/{case_id}/seller-response", response_model=FeedbackCase)
def seller_dispute_appeal(
    case_id: str,
    body: SubmitSellerCaseResponseRequest,
    auth: AuthContext = Depends(get_auth_context),
    feedback_svc: FeedbackService = Depends(get_feedback_service),
):
    """Seller submits response or evidence for a reported discrepancy (verified for shop owner)."""
    case = feedback_svc.ledger_repo.get_feedback_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    if auth.role != AuthContext().role:
        verify_seller_ownership(case.shop_id, auth)

    try:
        return feedback_svc.submit_seller_case_response(
            case_id=case_id,
            actor_id=auth.user_id or body.actor_id,
            response_text=body.response_text,
            proof_details=body.proof_details,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/feedback/cases/{case_id}/resolve", response_model=FeedbackCase)
def resolve_feedback_case(
    case_id: str,
    body: ResolveCaseRequest,
    auth: AuthContext = Depends(get_auth_context),
    feedback_svc: FeedbackService = Depends(get_feedback_service),
):
    """Operator or administrator resolves the dispute case."""
    require_admin_or_operator(auth)
    try:
        return feedback_svc.resolve_case(
            case_id=case_id,
            outcome=body.outcome,
            resolution_notes=body.resolution_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
