#!/usr/bin/env bash
# Переключает active_backend между app-blue и app-green в nginx.bluegreen.conf.
# Использование: bash scripts/switch_bluegreen.sh blue|green

set -euo pipefail

TARGET="${1:-}"
NGINX_CONF="docker/nginx/nginx.bluegreen.conf"

if [[ "${TARGET}" != "blue" && "${TARGET}" != "green" ]]; then
    echo "Usage: $0 blue|green" >&2
    exit 2
fi

if [[ ! -f "${NGINX_CONF}" ]]; then
    echo "Config not found: ${NGINX_CONF}" >&2
    exit 1
fi

case "${TARGET}" in
    blue)
        sed -i.bak -E 's|server app-(blue|green):8000;|server app-blue:8000;|' "${NGINX_CONF}"
        ;;
    green)
        sed -i.bak -E 's|server app-(blue|green):8000;|server app-green:8000;|' "${NGINX_CONF}"
        ;;
esac

rm -f "${NGINX_CONF}.bak"
echo "active_backend -> app-${TARGET}"
echo "Reload nginx: docker compose exec nginx nginx -s reload"
