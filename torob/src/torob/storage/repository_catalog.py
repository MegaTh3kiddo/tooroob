import json
from typing import Any, Dict, List, Optional, Tuple
import duckdb

from torob.domain.entities import Offer, Product, Shop
from torob.ingestion.normalizer import normalize_digits, normalize_persian_text
from torob.storage.db import db_manager


CATALOG_SYNONYMS: Dict[str, List[str]] = {
    "samsung": ["samsung", "سامسونگ"],
    "سامسونگ": ["samsung", "سامسونگ"],
    "apple": ["apple", "اپل", "آیفون", "ایفون"],
    "اپل": ["apple", "اپل", "آیفون", "ایفون"],
    "آیفون": ["apple", "اپل", "آیفون", "ایفون"],
    "ایفون": ["apple", "اپل", "آیفون", "ایفون"],
    "iphone": ["iphone", "آیفون", "ایفون", "apple", "اپل"],
    "galaxy": ["galaxy", "گلکسی"],
    "گلکسی": ["galaxy", "گلکسی"],
    "xiaomi": ["xiaomi", "شیائومی", "شیاومی"],
    "شیائومی": ["xiaomi", "شیائومی", "شیاومی"],
    "asus": ["asus", "ایسوس", "اسوس"],
    "ایسوس": ["asus", "ایسوس", "اسوس"],
    "lenovo": ["lenovo", "لنوو", "لنووو"],
    "لنوو": ["lenovo", "لنوو", "لنووو"],
    "hp": ["hp", "اچ پی", "اچ‌پی"],
    "sony": ["sony", "سونی"],
    "سونی": ["sony", "سونی"],
    "anker": ["anker", "انکر"],
    "انکر": ["anker", "انکر"],
    "logitech": ["logitech", "لاجیتک"],
    "لاجیتک": ["logitech", "لاجیتک"],
    "huawei": ["huawei", "هواوی"],
    "هواوی": ["huawei", "هواوی"],
}


class CatalogRepository:
    def __init__(self, con: Optional[duckdb.DuckDBPyConnection] = None):
        self._con = con

    @property
    def con(self) -> duckdb.DuckDBPyConnection:
        if self._con is not None:
            return self._con
        return db_manager.get_duckdb()

    def get_shop(self, shop_id: str) -> Optional[Shop]:
        query = "SELECT * FROM shops WHERE shop_id = ?"
        res = self.con.execute(query, [shop_id]).fetchone()
        if not res:
            return None
        return self._row_to_shop(res)

    def search_shops(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Shop], int]:
        filters = []
        params = []
        if q:
            norm_q = normalize_digits(normalize_persian_text(q)).lower().strip()
            tokens = [t for t in norm_q.split() if len(t) > 0]
            for tok in tokens:
                filters.append("(LOWER(name) LIKE ? OR LOWER(address) LIKE ?)")
                q_like = f"%{tok}%"
                params.extend([q_like, q_like])
        if category:
            cat_norm = normalize_digits(normalize_persian_text(category)).lower().strip()
            filters.append("LOWER(category_names) LIKE ?")
            params.append(f"%{cat_norm}%")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        
        count_q = f"SELECT COUNT(*) FROM shops {where_clause}"
        total = self.con.execute(count_q, params).fetchone()[0]

        select_q = f"SELECT * FROM shops {where_clause} LIMIT ? OFFSET ?"
        rows = self.con.execute(select_q, params + [limit, offset]).fetchall()
        return [self._row_to_shop(r) for r in rows], total

    def get_product(self, product_id: str) -> Optional[Product]:
        query = "SELECT * FROM products WHERE product_id = ?"
        res = self.con.execute(query, [product_id]).fetchone()
        if not res:
            return None
        return self._row_to_product(res)

    def search_products(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Product], int]:
        filters = []
        params = []
        if q:
            norm_q = normalize_digits(normalize_persian_text(q)).lower().replace("\u200c", " ").strip()
            tokens = [t for t in norm_q.split() if len(t) > 0]
            for tok in tokens:
                if tok in CATALOG_SYNONYMS:
                    syns = CATALOG_SYNONYMS[tok]
                    clause = " OR ".join(["LOWER(persian_title) LIKE ? OR LOWER(brand_name) LIKE ?" for _ in syns])
                    filters.append(f"({clause})")
                    for s in syns:
                        params.extend([f"%{s}%", f"%{s}%"])
                else:
                    filters.append("(LOWER(persian_title) LIKE ? OR LOWER(model) LIKE ?)")
                    q_like = f"%{tok}%"
                    params.extend([q_like, q_like])
        if category:
            cat_norm = normalize_digits(normalize_persian_text(category)).lower().strip()
            filters.append("LOWER(category_name) LIKE ?")
            params.append(f"%{cat_norm}%")
        if brand:
            brand_norm = brand.lower().strip()
            filters.append("LOWER(brand_name) = ?")
            params.append(brand_norm)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        
        count_q = f"SELECT COUNT(*) FROM products {where_clause}"
        total = self.con.execute(count_q, params).fetchone()[0]

        select_q = f"SELECT * FROM products {where_clause} LIMIT ? OFFSET ?"
        rows = self.con.execute(select_q, params + [limit, offset]).fetchall()
        return [self._row_to_product(r) for r in rows], total

    def get_offer(self, offer_id: str) -> Optional[Offer]:
        query = "SELECT * FROM offers WHERE offer_id = ?"
        res = self.con.execute(query, [offer_id]).fetchone()
        if not res:
            return None
        return self._row_to_offer(res)

    def get_offers_by_product(
        self, product_id: str, limit: int = 100, offset: int = 0
    ) -> List[Offer]:
        query = "SELECT * FROM offers WHERE product_id = ? ORDER BY price_toman ASC NULLS LAST LIMIT ? OFFSET ?"
        rows = self.con.execute(query, [product_id, limit, offset]).fetchall()
        return [self._row_to_offer(r) for r in rows]

    def get_offers_by_shop(
        self, shop_id: str, limit: int = 100, offset: int = 0
    ) -> List[Offer]:
        query = "SELECT * FROM offers WHERE shop_id = ? LIMIT ? OFFSET ?"
        rows = self.con.execute(query, [shop_id, limit, offset]).fetchall()
        return [self._row_to_offer(r) for r in rows]

    def get_peer_offers_loso(
        self, product_id: str, exclude_shop_id: str
    ) -> List[Offer]:
        """Fetch all comparable competitor offers for a product, excluding the given shop (Leave-One-Shop-Out)."""
        query = """
        SELECT * FROM offers 
        WHERE product_id = ? 
          AND shop_id != ? 
          AND price_toman IS NOT NULL 
          AND price_toman > 1
        ORDER BY price_toman ASC
        """
        rows = self.con.execute(query, [product_id, exclude_shop_id]).fetchall()
        return [self._row_to_offer(r) for r in rows]

    def _row_to_shop(self, row) -> Shop:
        # Columns: shop_id, name, address, lat, lon, location_label, category_names,
        # payment_options, supports_fast_delivery, website_url, weekly_hours, contacts, instagram
        cat_names = []
        if row[6]:
            try:
                cat_names = json.loads(row[6]) if row[6].startswith("[") else [row[6]]
            except Exception:
                cat_names = [row[6]]

        weekly_h = None
        if row[10]:
            try:
                weekly_h = json.loads(row[10])
            except Exception:
                weekly_h = None

        return Shop(
            shop_id=row[0],
            name=row[1] or "",
            address=row[2],
            lat=row[3],
            lon=row[4],
            location_label=row[5],
            category_names=cat_names,
            payment_options=row[7],
            supports_fast_delivery=bool(row[8]),
            website_url=row[9],
            weekly_hours=weekly_h,
            contacts=row[11],
            instagram=row[12],
        )

    def _row_to_product(self, row) -> Product:
        # Columns: product_id, persian_title, brand_name, category_name, model, image_urls, specs
        img_urls = []
        if row[5]:
            try:
                img_urls = json.loads(row[5]) if row[5].startswith("[") else [row[5]]
            except Exception:
                img_urls = [row[5]]

        specs_dict = {}
        if row[6]:
            try:
                specs_dict = json.loads(row[6]) if row[6].startswith("{") else {}
            except Exception:
                specs_dict = {}

        return Product(
            product_id=row[0],
            persian_title=row[1] or "",
            brand_name=row[2],
            category_name=row[3],
            model=row[4],
            image_urls=img_urls,
            specs=specs_dict,
        )

    def _row_to_offer(self, row) -> Offer:
        # Columns: offer_id, product_id, shop_id, price_toman, last_price_changed_at, seller_title, warranty, description
        return Offer(
            offer_id=row[0],
            product_id=row[1],
            shop_id=row[2],
            price_toman=row[3],
            last_price_changed_at=row[4],
            seller_title=row[5],
            warranty=row[6],
            description=row[7],
        )
