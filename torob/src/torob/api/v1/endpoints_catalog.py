from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from torob.api.dependencies import get_catalog_repo
from torob.api.v1.schemas import HealthResponse, PaginatedResponse
from torob.core.config import settings
from torob.domain.entities import Offer, Product, Shop
from torob.storage.repository_catalog import CatalogRepository

router = APIRouter(tags=["Catalog & Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(repo: CatalogRepository = Depends(get_catalog_repo)):
    """Check backend operational health and verify loaded catalog row counts."""
    con = repo.con
    try:
        shops_cnt = con.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
        prods_cnt = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        offers_cnt = con.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
    except Exception:
        shops_cnt, prods_cnt, offers_cnt = 0, 0, 0

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        catalog_counts={
            "shops": shops_cnt,
            "products": prods_cnt,
            "offers": offers_cnt,
        },
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/products", response_model=PaginatedResponse[Product])
def list_products(
    q: Optional[str] = Query(None, description="Search term in title or model"),
    category: Optional[str] = Query(None, description="Category filter"),
    brand: Optional[str] = Query(None, description="Brand filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: CatalogRepository = Depends(get_catalog_repo),
):
    """Search and paginate products in the Torob catalog."""
    items, total = repo.search_products(q=q, category=category, brand=brand, limit=limit, offset=offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str, repo: CatalogRepository = Depends(get_catalog_repo)):
    """Retrieve detailed product specifications by ID."""
    prod = repo.get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return prod


@router.get("/products/{product_id}/offers", response_model=List[Offer])
def get_product_offers(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: CatalogRepository = Depends(get_catalog_repo),
):
    """Retrieve all seller offers for a specific product, ordered by price."""
    return repo.get_offers_by_product(product_id, limit=limit, offset=offset)


@router.get("/shops", response_model=PaginatedResponse[Shop])
def list_shops(
    q: Optional[str] = Query(None, description="Search term in shop name or address"),
    category: Optional[str] = Query(None, description="Category filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: CatalogRepository = Depends(get_catalog_repo),
):
    """Search and paginate physical shops."""
    items, total = repo.search_shops(q=q, category=category, limit=limit, offset=offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/shops/{shop_id}", response_model=Shop)
def get_shop(shop_id: str, repo: CatalogRepository = Depends(get_catalog_repo)):
    """Retrieve physical shop location, address, hours and contacts."""
    shop = repo.get_shop(shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_id} not found")
    return shop


@router.get("/shops/{shop_id}/offers", response_model=List[Offer])
def get_shop_offers(
    shop_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: CatalogRepository = Depends(get_catalog_repo),
):
    """Retrieve offers listed by a specific shop (capped at 300)."""
    return repo.get_offers_by_shop(shop_id, limit=limit, offset=offset)


@router.get("/offers/{offer_id}", response_model=Offer)
def get_offer(offer_id: str, repo: CatalogRepository = Depends(get_catalog_repo)):
    """Retrieve a single offer by ID."""
    offer = repo.get_offer(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")
    return offer
