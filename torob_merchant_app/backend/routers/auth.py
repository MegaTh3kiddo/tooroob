import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
from database import get_db
from models import RequestOtpRequest, RequestOtpResponse, VerifyOtpRequest, TokenResponse, SellerDto
from services.sms_service import send_otp, verify_otp
from config import settings

router = APIRouter(prefix="/seller/auth", tags=["Seller Auth"])

def get_current_seller(authorization: str = Header(None)) -> SellerDto:
    """Simple Bearer token resolution for seller."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="اعتبارسنجی نامعتبر است. لطفا مجددا وارد شوید.")
    
    token = authorization.replace("Bearer ", "").strip()
    # Simple token scheme: token is either seller_id or a simulated JWT token
    seller_id = token.replace("token_", "") if token.startswith("token_") else token
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id, phone_number, shop_id, full_name, is_active FROM sellers WHERE seller_id = ?", (seller_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="حساب کاربری یافت نشد")

    return SellerDto(
        seller_id=row["seller_id"],
        phone_number=row["phone_number"],
        shop_id=row["shop_id"],
        full_name=row["full_name"],
        is_active=bool(row["is_active"])
    )

from services.voice.phone_utils import normalize_phone_number, is_valid_phone, is_iranian_landline
from services.voice.voice_service import voice_service
from services.voice.models import CallStatus
from services.sms_service import send_otp, verify_otp, generate_secure_otp

@router.post("/request-otp", response_model=RequestOtpResponse)
async def request_otp_endpoint(payload: RequestOtpRequest):
    phone = normalize_phone_number(payload.phone_number)
    if not is_valid_phone(phone):
        raise HTTPException(status_code=400, detail="شماره تلفن وارد شده نامعتبر است")

    # Determine whether to deliver via voice call (landline) or SMS (mobile)
    if is_iranian_landline(phone):
        is_limited, err_msg, code = generate_secure_otp(phone)
        if is_limited:
            raise HTTPException(status_code=429, detail=err_msg)

        # Dispatch Voice Call via Poshteyar
        call_result = await voice_service.dispatch_landline_otp(phone, code)
        if call_result.status == CallStatus.FAILED:
            error_msg = call_result.message or "برقراری تماس صوتی با خطا مواجه شد"
            raise HTTPException(status_code=500, detail=f"خطا در تماس صوتی: {error_msg}")

        demo_otp = code if (settings.OUTBOUND_CALL_PROVIDER == "mock" or not settings.POSHTYAR_API_KEY) else None
        return RequestOtpResponse(
            success=True,
            message="کد تایید به صورت تماس صوتی به خط ثابت فروشگاه شما اعلام خواهد شد.",
            demo_otp=demo_otp,
            delivery_method="voice_call"
        )
    else:
        # Standard Mobile SMS Flow
        success, msg, code = send_otp(phone)
        if not success:
            raise HTTPException(status_code=429, detail=msg)

        demo_otp = code if (settings.SMS_PROVIDER == "mock" or not settings.SMS_API_KEY) else None
        return RequestOtpResponse(
            success=True,
            message=msg,
            demo_otp=demo_otp,
            delivery_method="sms"
        )

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp_endpoint(payload: VerifyOtpRequest):
    phone = normalize_phone_number(payload.phone_number)
    code = payload.otp_code.strip()

    if not verify_otp(phone, code):
        raise HTTPException(status_code=400, detail="کد تایید وارد شده نادرست یا منقضی شده است")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id, phone_number, shop_id, full_name, is_active FROM sellers WHERE phone_number = ?", (phone,))
    row = cursor.fetchone()

    if not row:
        # Auto-register new seller linked to default shop
        seller_id = f"seller_{uuid.uuid4().hex[:8]}"
        shop_id = "shop_51d0c1a6edf81ba759726bab"
        full_name = "فروشنده جدید"
        cursor.execute("""
        INSERT INTO sellers (seller_id, phone_number, shop_id, full_name)
        VALUES (?, ?, ?, ?)
        """, (seller_id, phone, shop_id, full_name))
        conn.commit()
        seller_dto = SellerDto(seller_id=seller_id, phone_number=phone, shop_id=shop_id, full_name=full_name, is_active=True)
    else:
        seller_dto = SellerDto(
            seller_id=row["seller_id"],
            phone_number=row["phone_number"],
            shop_id=row["shop_id"],
            full_name=row["full_name"],
            is_active=bool(row["is_active"])
        )

    conn.close()

    token = f"token_{seller_dto.seller_id}"
    return TokenResponse(access_token=token, seller=seller_dto)

@router.get("/me", response_model=SellerDto)
def get_me(seller: SellerDto = Depends(get_current_seller)):
    return seller
