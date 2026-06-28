#!/bin/bash
set -e

# Função que espera o postgres ficar pronto antes de subir o server
function_postgres_ready() {
python << END
import socket
import time
import os

port = int(os.environ["POSTGRES_PORT"])
host = os.environ["POSTGRES_HOST"]

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect((host, port))
s.close()
END
}

until function_postgres_ready; do
  >&2 echo "======= POSTGRES IS UNAVAILABLE, WAITING"
  sleep 1
done
echo "======= POSTGRES IS UP, CONNECTING"

echo '======= RUNNING MIGRATIONS'
python3 manage.py migrate --noinput

# load_initial_data popula entidades suportadas. Em prod, rodar a cada
# subida pode re-popular/sobrescrever, condicionado por env. Ligar no
# 1o deploy (RUN_LOAD_INITIAL_DATA=true) e desligar depois.
if [ "${RUN_LOAD_INITIAL_DATA:-true}" = "true" ]; then
  echo '======= PREPOPULATING THE DATABASE'
  python3 manage.py load_initial_data
else
  echo '======= SKIPPING load_initial_data (RUN_LOAD_INITIAL_DATA != true)'
fi

echo '======= COLLECTING STATIC FILES'
python3 manage.py collectstatic --noinput

# ATENCAO scheduler: o APScheduler sobe no ready() do AppConfig, uma vez
# por worker do gunicorn. A eleicao de lider via advisory lock do Postgres
# (releases/jobs.py:acquire_scheduler_lock) garante que so 1 worker starta
# o cron mesmo com GUNICORN_WORKERS>1. Se o banco nao suportar advisory
# lock, force GUNICORN_WORKERS=1.
echo '======= RUNNING GUNICORN'
exec gunicorn config.wsgi:application \
  --chdir /src \
  --bind 0.0.0.0:8080 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
