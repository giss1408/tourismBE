#!/bin/sh
# Compressed PostgreSQL dump into $1 (default ./backups), keeping the last
# BACKUP_RETENTION_DAYS days (default 14). Copy the folder off the server
# (object storage, another host) so a lost server does not lose the backups.
set -eu
target="${1:-./backups}"
retention="${BACKUP_RETENTION_DAYS:-14}"
mkdir -p "$target"
file="$target/tourism-$(date -u +%Y%m%d-%H%M%S).sql.gz"
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip > "$file"
find "$target" -name 'tourism-*.sql.gz' -mtime +"$retention" -delete
echo "Backup written to $file"
