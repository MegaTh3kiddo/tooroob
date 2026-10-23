#!/usr/bin/env bash
# One-shot Liara deployment of backend (torobmap-api) + web (torobmap).
# Usage: LIARA_TOKEN=... ./scripts/deploy_liara.sh   (requires @liara/cli and account balance)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="${WEB_DIR:-$ROOT/../trobapp}"
T=(--api-token "${LIARA_TOKEN:?set LIARA_TOKEN}")
NET="${LIARA_NETWORK:-torobnet}"

liara network create -n "$NET" "${T[@]}" </dev/null || true
liara app create -a torobmap-api --platform docker --plan standard-plus-g2 --feature-plan basic -n "$NET" "${T[@]}" </dev/null || true
liara app create -a torobmap --platform next --plan medium-g2 --feature-plan basic -n "$NET" "${T[@]}" </dev/null || true
liara disk create -a torobmap-api --name ledger --size 2 "${T[@]}" </dev/null || true
liara env set -a torobmap-api "TOROB_CORS_ORIGINS=https://torobmap.liara.run" --force "${T[@]}" </dev/null || true

(cd "$ROOT/data" && for f in shops products offers; do [ -f "$f.csv.gz" ] || gzip -k "$f.csv"; done)
(cd "$ROOT" && liara deploy --no-app-logs "${T[@]}" </dev/null)
(cd "$WEB" && liara deploy --no-app-logs "${T[@]}" </dev/null)

curl -fsS https://torobmap-api.liara.run/api/v1/health && echo
echo "Web: https://torobmap.liara.run   API: https://torobmap-api.liara.run/docs"
