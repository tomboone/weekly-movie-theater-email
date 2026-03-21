#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose -f docker-compose.prod.yml pull --quiet
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker image prune -f --filter "until=168h" > /dev/null 2>&1
