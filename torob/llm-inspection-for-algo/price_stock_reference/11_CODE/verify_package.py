"""Validate the unzipped reference pack; does not modify content.
Run from any directory: python path/to/11_CODE/verify_package.py
"""
from pathlib import Path
import csv, json, hashlib, sys
R=Path(__file__).resolve().parents[1]
failed=[]; checks=[]
def require(condition,message):
    checks.append((bool(condition),message))
    if not condition:failed.append(message)

audit=json.loads((R/'02_DATA/verified_audit.json').read_text(encoding='utf8'))
reference={"shops.csv":6476,"products.csv":225903,"offers.csv":331506}
for f,expected in reference.items():
    p=R/'10_SOURCE_DATA'/f
    require(p.is_file(),f'raw source present: {f}')
    if p.is_file():
        with p.open(encoding='utf8',newline='') as h:n=sum(1 for _ in csv.reader(h))-1
        require(n==expected,f'{f} row count expected {expected}, got {n}')
        dig=hashlib.sha256(p.read_bytes()).hexdigest()
        require(dig==audit['source_sha256'][f],f'{f} checksum matches audit')
for f in ['README.txt','price_audit_candidates.csv']:
    p=R/'10_SOURCE_DATA'/f
    require(p.is_file(),f'raw source present: {f}')
    if p.is_file():require(hashlib.sha256(p.read_bytes()).hexdigest()==audit['source_sha256'][f],f'{f} checksum matches audit')
with (R/'06_QUALITY/edge_case_register.csv').open(encoding='utf-8-sig',newline='') as h:rows=list(csv.DictReader(h))
require(len(rows)==180,f'180 edge cases (got {len(rows)})')
require(len(set(row['id'] for row in rows))==len(rows),'edge IDs unique')
require(len(set(row['domain'] for row in rows))==20,'20 edge domains')
require(all(row['scenario'] and row['required_behavior'] and row['acceptance_test'] for row in rows),'edge scenario, expected behavior, acceptance text nonempty')
with (R/'02_DATA/price_audit_candidates_review_only.csv').open(encoding='utf-8-sig',newline='') as h:count=sum(1 for _ in csv.reader(h))-1
require(count==19458,f'price audit review list 19458 rows (got {count})')
md=list(R.rglob('*.md'))
require(len(md)>=28,f'markdown document count >=28: {len(md)}')
require(all(len(p.read_text(encoding='utf8'))>=90 for p in md),'no empty docs')
html=R/'00_START/All_Documents_Readable.html'
require(html.is_file() and html.stat().st_size>100000,'full readable HTML present')
for codefile in ['baseline_reference.py','schema.sql','sample_policy.yaml','evidence.schema.json','reproduce_audit.py','test_baseline.py']:
    require((R/'11_CODE'/codefile).is_file(),f'code present: {codefile}')
with (R/'11_CODE/evidence.schema.json').open(encoding='utf8') as h:schema=json.load(h)
require(schema['type']=='object','JSON event schema parse')
try:
    import yaml
    with (R/'11_CODE/sample_policy.yaml').open(encoding='utf8') as h:pol=yaml.safe_load(h)
    require(pol['probability_claim_allowed'] is False,'MVP cannot expose uncalibrated probabilities')
    require(pol['stock']['never_use_no_response_as_out_of_stock'] is True,'no response not treated as stock-out')
except ImportError:
    print('INFO: PyYAML unavailable; YAML syntax verification skipped')
# Semantic coverage through traceability registry
trace=(R/'00_START/03_Conversation_Traceability.md').read_text(encoding='utf8')
for term in ['نوسان','محصول تازه','دلار','نشان بیرونی','فیدبک','بازبودن','استعلام','پاسخ','شارژ','آدرس','گارانتی']:
    require(term in trace,f'topic traceability: {term}')
# Audit numerical sanity
require(audit['counts']['offers']==331506 and audit['counts']['products']==225903,'audit counts match sources')
require(audit['timestamps']['null_or_invalid']==769,'missing timestamps explicitly audited')
require(audit['counts']['pairs_with_multiple_offers']==9557,'multi-offer pair evidence')
require(audit['prices']['positive_below_1000']>=audit['prices']['exactly_one_toman'],'overlap of flags understood')
print('PACKAGE REVIEW SUMMARY',len(checks),'checks')
for ok,desc in checks:print(('PASS' if ok else 'FAIL'),desc)
if failed:print('FAILURES:',failed);sys.exit(1)
print('ALL CHECKS PASSED')
