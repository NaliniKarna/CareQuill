#!/usr/bin/env bash
# Restore a backup made by backup.sh. DESTRUCTIVE: replaces the database and
# the uploaded files with the backup. Stop and think before running it.
#
#   ./scripts/restore.sh backups/db_2026-10-08_030000.sql.gz backups/files_2026-10-08_030000.tar.gz
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <db_*.sql.gz> <files_*.tar.gz>" >&2
  exit 1
fi
DB_FILE="$1"
FILES_FILE="$2"
[ -s "$DB_FILE" ] && [ -s "$FILES_FILE" ] || { echo "Backup file missing or empty." >&2; exit 1; }

cd "$(dirname "$0")/.."
ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE")
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

read -r -p "This REPLACES all current data with the backup. Type RESTORE to continue: " answer
[ "$answer" = "RESTORE" ] || { echo "Cancelled."; exit 1; }

"${COMPOSE[@]}" stop backend
"${COMPOSE[@]}" exec -T db psql -U "${POSTGRES_USER:-medqueue}" -d postgres \
  -c "DROP DATABASE IF EXISTS \"${POSTGRES_DB:-medqueue_ai}\" WITH (FORCE);" \
  -c "CREATE DATABASE \"${POSTGRES_DB:-medqueue_ai}\";"
gunzip -c "$DB_FILE" | "${COMPOSE[@]}" exec -T db \
  psql -U "${POSTGRES_USER:-medqueue}" -d "${POSTGRES_DB:-medqueue_ai}" -v ON_ERROR_STOP=1

"${COMPOSE[@]}" run --rm --no-deps -T backend sh -c 'rm -rf /app/storage/* /app/storage/.[!.]* 2>/dev/null; true'
"${COMPOSE[@]}" run --rm --no-deps -T backend tar -C /app/storage -xzf - < "$FILES_FILE"
"${COMPOSE[@]}" start backend
echo "Restore finished. Check the site, then log in and open a document."
