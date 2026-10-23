"""Recompute core metrics from included source files; no external connections needed.
Requirements: pandas. Run: python 11_CODE/reproduce_audit.py
Produces verified_audit_recomputed.json in 02_DATA (does not overwrite original).
"""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'10_SOURCE_DATA'; O=ROOT/'02_DATA'
def normalize(x):return x.mask(x.isin(['null','','None','NULL','NaN']))
shops=pd.read_csv(S/'shops.csv',dtype=str,keep_default_na=False)
products=pd.read_csv(S/'products.csv',dtype=str,keep_default_na=False)
offers=pd.read_csv(S/'offers.csv',dtype=str,keep_default_na=False)
prices=pd.to_numeric(normalize(offers.price_toman),errors='coerce')
ts=pd.to_datetime(normalize(offers.last_price_changed_at),utc=True,errors='coerce')
base=pd.Timestamp('2026-10-22 20:30:00+00:00')
age=(base-ts).dt.total_seconds()/86400
nshops=offers.groupby('product_id').shop_id.nunique()
pairs=offers.groupby(['shop_id','product_id']).size()
results={
 'shops':len(shops),'products':len(products),'offers':len(offers),
 'categories':int(products.category_name.nunique()),
 'shops_with_offers':int(offers.shop_id.nunique()),
 'missing_price':int(prices.isna().sum()),'one_toman':int((prices==1).sum()),
 'below_1000_positive':int(((prices>0)&(prices<1000)).sum()),
 'price_above_1e12':int((prices>1e12).sum()),
 'missing_timestamp':int(ts.isna().sum()),
 'timestamp_max':str(ts.max()),
 'age_median_days':round(float(age.median()),2),
 'age_p90_days':round(float(age.quantile(.9)),2),
 'shop_product_pairs':len(pairs),
 'pairs_multiple_offers':int((pairs>1).sum()),
 'products_2plus_shops':int((nshops>=2).sum()),
 'shops_websites':int((~shops.website_url.isin(['null',''])).sum()),
 'shops_empty_weekly_hours':int(shops.weekly_hours.isin(['null','','{}']).sum()),
 'shops_exactly_300_products':int((offers.groupby('shop_id').product_id.nunique()==300).sum())
}
with (O/'verified_audit_recomputed.json').open('w',encoding='utf8') as f:json.dump(results,f,ensure_ascii=False,indent=2)
print(json.dumps(results,ensure_ascii=False,indent=2))
