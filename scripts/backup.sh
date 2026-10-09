#!/usr/bin/env bash
# Nightly backup for the VPS deployment: Postgres dump + uploaded documents.
#
#   ./scripts/backup.sh                 # writes to ./backups, keeps 14 days
#   BACKUP_DIR=/mnt/backup KEEP_DAYS=30 ./scripts/backup.sh
#
# Run from the repo folder (cron example in docs/deployment.md). Copy the
# backups OFF this server too (rclone, scp, a second provider): a backup on
# the same disk does not survive losing the server.
set -euo pipefail

cd "$(dirname "$0")/.."
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE")

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

stamp="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
umask 077   # backups hold patient data: owner-only files

echo "Dumping database..."
"${COMPOSE[@]}" exec -T db \
  pg_dump -U "${POSTGRES_USER:-medqueue}" -d "${POSTGRES_DB:-medqueue_ai}" --no-owner \
  | gzip > "$BACKUP_DIR/db_$stamp.sql.gz"

echo "Archiving uploaded documents..."
"${COMPOSE[@]}" exec -T backend tar -C /app/storage -czf - . \
  > "$BACKUP_DIR/files_$stamp.tar.gz"

# A failed pipe would leave an empty file: refuse to keep those.
for f in "$BACKUP_DIR/db_$stamp.sql.gz" "$BACKUP_DIR/files_$stamp.tar.gz"; do
  [ -s "$f" ] || { echo "Backup file is empty: $f" >&2; exit 1; }
done

find "$BACKUP_DIR" -type f \( -name 'db_*.sql.gz' -o -name 'files_*.tar.gz' \) \
  -mtime +"$KEEP_DAYS" -delete

echo "Done: $BACKUP_DIR/db_$stamp.sql.gz and files_$stamp.tar.gz"
