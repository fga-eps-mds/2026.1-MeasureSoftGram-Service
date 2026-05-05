"""
Development settings — DJANGO_SETTINGS_MODULE=config.settings.dev

DEBUG ligado, ALLOWED_HOSTS aberto, CREATE_FAKE_DATA por default.
INTERNAL_IPS computado dinamicamente para o debug-toolbar funcionar dentro
do container Docker.
"""

import socket

from .base import *  # noqa: F401,F403


DEBUG = True

ALLOWED_HOSTS = ["*"]

# Default em dev: popula banco com fake data via load_initial_data.
CREATE_FAKE_DATA = True

# debug-toolbar: descobrir IPs internos do container pra liberar a barra.
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + [
    "127.0.0.1",
    "10.0.2.2",
]
