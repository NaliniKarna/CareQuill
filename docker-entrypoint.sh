#!/bin/sh
# Named volumes keep whatever ownership they were first created with (for
# example root, from an older image), which would make uploads fail with
# "Permission denied". Fix the ownership of the storage directory, then drop
# root privileges and run the real command as the unprivileged `app` user.
set -e
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/storage/medical_documents
    chown -R app:app /app/storage
    exec setpriv --reuid=app --regid=app --init-groups "$@"
fi
exec "$@"
