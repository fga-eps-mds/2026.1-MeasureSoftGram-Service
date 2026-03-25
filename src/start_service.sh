#!/bin/bash

# Exporting all environment variables to use in crontab
env | sed 's/^\(.*\)$/ \1/g' > /root/env

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
python3 manage.py migrate

echo '======= PREPOPULATING THE DATABASE'
python3 manage.py load_initial_data

echo '======= COLLECTING STATIC FILES'
python3 manage.py collectstatic --noinput

echo '======= RUNNING SERVER'
python3 manage.py runserver 0.0.0.0:8080
