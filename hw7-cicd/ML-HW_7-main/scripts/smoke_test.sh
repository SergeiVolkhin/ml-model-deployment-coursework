#!/usr/bin/env bash
# Smoke test: 100 запросов к /predict через nginx, подсчёт долей по X-Service-Version.
# Использование: bash scripts/smoke_test.sh [URL] [COUNT]

set -euo pipefail

URL="${1:-http://localhost:8080}"
COUNT="${2:-100}"
PAYLOAD='{"x":[5.1,3.5,1.4,0.2]}'

echo "[smoke] target=${URL} count=${COUNT}"

if ! curl -fsS "${URL}/health" >/dev/null; then
    echo "[smoke] /health is not available" >&2
    exit 1
fi

stable=0
canary=0
other=0
errors=0

for i in $(seq 1 "${COUNT}"); do
    response=$(curl -sS -o /dev/null -w '%{http_code} %{header_json}' \
        -X POST "${URL}/predict" \
        -H "Content-Type: application/json" \
        -d "${PAYLOAD}" || true)
    code="${response%% *}"
    headers="${response#* }"

    if [[ "${code}" != "200" ]]; then
        errors=$((errors + 1))
        continue
    fi

    version=$(echo "${headers}" | grep -oE '"x-service-version":\["[^"]+' | head -1 | sed 's/.*"\([^"]*\)$/\1/')
    case "${version}" in
        v1.0.0) stable=$((stable + 1)) ;;
        v1.1.0) canary=$((canary + 1)) ;;
        *)      other=$((other + 1)) ;;
    esac
done

echo "[smoke] stable v1.0.0: ${stable}"
echo "[smoke] canary v1.1.0: ${canary}"
echo "[smoke] other: ${other}"
echo "[smoke] errors: ${errors}"

if [[ "${errors}" -gt 0 ]]; then
    exit 1
fi
