# Torob Intelligence Engine — production image (Liara / any Docker host)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    TZ=Asia/Tehran \
    TOROB_ENV=production \
    TOROB_SQLITE_PATH=/data/torob_ledger.db \
    PORT=8080

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r requirements.txt

COPY configs ./configs
# Optional runtime config (.env, e.g. LLM provider key); Liara panel env vars override it
COPY .env* ./
COPY src ./src
# Catalogue snapshot (gzip CSVs, read directly by DuckDB at startup)
COPY data/shops.csv.gz data/products.csv.gz data/offers.csv.gz ./data/

RUN mkdir -p /data
EXPOSE 8080
CMD ["sh", "-c", "uvicorn torob.api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
