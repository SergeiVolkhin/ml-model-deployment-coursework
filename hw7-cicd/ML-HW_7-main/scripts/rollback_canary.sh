#!/usr/bin/env bash
# Откат на 100% stable: подменяем nginx.conf на статический без split_clients.
# Использование: bash scripts/rollback_canary.sh

set -euo pipefail

NGINX_CONTAINER="${NGINX_CONTAINER:-ml-nginx}"

START=$(date +%s%3N)
echo "[rollback] switching to stable-only config"

docker exec "${NGINX_CONTAINER}" sh -c "cp /templates/nginx.rollback.conf /etc/nginx/nginx.conf"
docker exec "${NGINX_CONTAINER}" nginx -s reload

END=$(date +%s%3N)
echo "[rollback] done in $((END - START)) ms"
