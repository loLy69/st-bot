#!/usr/bin/env bash
set -euo pipefail

cd /opt/mindspark
mkdir -p backups
stamp="$(date +%Y%m%d-%H%M%S)"
docker compose exec -T bot python -c "import sqlite3; src=sqlite3.connect('/app/data/mindspark.db'); dst=sqlite3.connect('/app/data/backup.db'); src.backup(dst); dst.close(); src.close()"
container_id="$(docker compose ps -q bot)"
docker cp "${container_id}:/app/data/backup.db" "backups/mindspark-${stamp}.db"
docker compose exec -T bot rm -f /app/data/backup.db
find backups -type f -name 'mindspark-*.db' -mtime +14 -delete
