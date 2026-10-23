from fastapi import APIRouter

from torob.api.v1.endpoints_admin import router as admin_router
from torob.api.v1.endpoints_assessment import router as assessment_router
from torob.api.v1.endpoints_assistant import router as assistant_router
from torob.api.v1.endpoints_catalog import router as catalog_router
from torob.api.v1.endpoints_customer import router as customer_router
from torob.api.v1.endpoints_feedback import router as feedback_router
from torob.api.v1.endpoints_inquiries import router as inquiries_router
from torob.api.v1.endpoints_plans import router as plans_router
from torob.api.v1.endpoints_seller import router as seller_router
from torob.api.v1.endpoints_visits import router as visits_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(catalog_router)
api_v1_router.include_router(assessment_router)
api_v1_router.include_router(inquiries_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(visits_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(assistant_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(customer_router)
api_v1_router.include_router(seller_router)
