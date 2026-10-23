from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query

from torob.api.dependencies import get_inquiry_service, get_ledger_repo
from torob.api.v1.schemas import (
    CreateInquiryRequest,
    CreateInquiryResponse,
    SubmitSellerResponseRequest,
)
from torob.core.security import AuthContext, get_auth_context, verify_seller_ownership
from torob.domain.entities import Inquiry
from torob.inquiries.service import InquiryService
from torob.storage.repository_ledger import LedgerRepository

router = APIRouter(tags=["Seller Inquiries & Workflow"])


@router.post("/inquiries", response_model=CreateInquiryResponse, status_code=201)
def create_or_join_inquiry(
    body: CreateInquiryRequest,
    inquiry_svc: InquiryService = Depends(get_inquiry_service),
):
    """Create a new verification inquiry for a shop or coalesce with an existing active one."""
    inquiry, is_new = inquiry_svc.create_inquiry(
        shop_id=body.shop_id,
        product_id=body.product_id,
        offer_id=body.offer_id,
        question_scope=body.question_scope,
        priority=body.priority,
    )
    msg = "استعلام جدید با موفقیت ثبت و ارسال شد" if is_new else "استعلام فعال قبلی برای این پیشنهاد بازیابی شد (عدم مزاحمت مکرر)"
    return CreateInquiryResponse(inquiry=inquiry, is_new=is_new, message=msg)


@router.get("/inquiries/{inquiry_id}", response_model=Inquiry)
def get_inquiry_status(
    inquiry_id: str,
    inquiry_svc: InquiryService = Depends(get_inquiry_service),
):
    """Get the current status, deadline, and scope of an inquiry."""
    inq = inquiry_svc.get_inquiry(inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")
    return inq


@router.post("/inquiries/{inquiry_id}/responses")
def submit_seller_inquiry_response(
    inquiry_id: str,
    body: SubmitSellerResponseRequest,
    auth: AuthContext = Depends(get_auth_context),
    inquiry_svc: InquiryService = Depends(get_inquiry_service),
):
    """Submit seller confirmation or price/stock correction with ownership validation."""
    inq = inquiry_svc.get_inquiry(inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

    # If role is provided, enforce seller ownership
    if auth.role != AuthContext().role:  # non-public
        verify_seller_ownership(inq.shop_id, auth)

    try:
        res = inquiry_svc.submit_seller_response(
            inquiry_id=inquiry_id,
            actor_id=auth.user_id or body.actor_id,
            confirmed_price=body.confirmed_price,
            confirmed_stock_state=body.confirmed_stock_state,
            shop_is_open=body.shop_is_open,
            notes=body.notes,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/shops/{shop_id}/inquiries", response_model=List[Inquiry])
def get_shop_active_inbox(
    shop_id: str,
    auth: AuthContext = Depends(get_auth_context),
    inquiry_svc: InquiryService = Depends(get_inquiry_service),
):
    """Retrieve active inquiry inbox for a seller portal (authorized for shop owner or admin)."""
    if auth.role != AuthContext().role:
        verify_seller_ownership(shop_id, auth)
    return inquiry_svc.list_shop_inquiries(shop_id)
