#!/usr/bin/env bash
# Поэтапное увеличение веса canary: 10 -> 25 -> 50 -> 100.
# Между этапами 60 секунд паузы и проверка /health обоих апстримов.
# При неудаче health-check автоматически вызывается rollback_canary.sh.
#
# Использование: bash scripts/deploy_canary.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NGINX_URL="${NGINX_URL:-http://localhost:8080/health}"
ROLLBACK_FLAG="${ROLLBACK_FLAG:-/tmp/rollback}"
WAIT_BETWEEN="${WAIT_BETWEEN:-60}"
NGINX_CONTAINER="${NGINX_CONTAINER:-ml-nginx}"
STAGES=(10 25 50 100)

health_check() {
    local name="$1"
    if ! docker exec "${name}" python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200 else 1)"; then
        echo "[health] ${name}: FAIL"
        return 1
    fi
    echo "[health] ${name}: ok"
}

set_weight() {
    local weight="$1"
    echo "[stage] CANARY_WEIGHT=${weight}"
    docker exec -e CANARY_WEIGHT="${weight}" "${NGINX_CONTAINER}" sh -c \
        "DOLLAR='\$' envsubst '\$DOLLAR \$CANARY_WEIGHT' < /templates/nginx.canary.conf.template > /etc/nginx/nginx.conf"
    docker exec "${NGINX_CONTAINER}" nginx -s reload
}

rollback_and_exit() {
    echo "[error] rollback triggered"
    bash "${ROOT_DIR}/scripts/rollback_canary.sh"
    exit 1
}

trap 'rollback_and_exit' ERR

for weight in "${STAGES[@]}"; do
    set_weight "${weight}"

    if [[ -f "${ROLLBACK_FLAG}" ]]; then
        echo "[abort] rollback flag detected: ${ROLLBACK_FLAG}"
        rollback_and_exit
    fi

    if [[ "${weight}" == "100" ]]; then
        echo "[done] canary fully promoted"
        break
    fi

    echo "[wait] sleeping ${WAIT_BETWEEN}s before next stage"
    sleep "${WAIT_BETWEEN}"

    health_check ml-service-stable || rollback_and_exit
    health_check ml-service-canary || rollback_and_exit

    curl -fsS "${NGINX_URL}" >/dev/null || rollback_and_exit
done
