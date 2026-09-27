#!/bin/sh
# Runs the daily jobs with cron (scheduler service of the production stack):
#   09:00 UTC  trip reminders (push, the day before check-in)
#   02:30 UTC  database backup into /backups
set -eu
# cron starts jobs with an empty environment: hand them the configuration.
printenv | grep -v -E '^(HOME|PWD|SHLVL|_)=' | sed "s/'/'\\\\''/g; s/=\(.*\)/='\1'/; s/^/export /" > /etc/job.env
cat > /etc/cron.d/tourism <<'CRON'
0 9 * * * root . /etc/job.env; cd /app && python manage.py send_trip_reminders >> /proc/1/fd/1 2>&1
30 2 * * * root . /etc/job.env; /app/scripts/backup_db.sh /backups >> /proc/1/fd/1 2>&1
CRON
chmod 0644 /etc/cron.d/tourism
exec cron -f
