"""
Production settings — DJANGO_SETTINGS_MODULE=config.settings.production

DEBUG=False forcado. Headers de seguranca (HSTS, SSL redirect, cookies
secure-only) sao PARAMETRIZADOS por env e vem DESLIGADOS por default,
porque o deploy atras de proxy HTTP plano (sem TLS na box) quebra com
SSL redirect forcado: o Django responde HTTP interno e um redirect pra
https sem certificado vira loop, e o HSTS gravado no browser trava o
acesso futuro. Quando houver TLS na borda, ligar via env. Backward-
compatible com env vars existentes (SECRET_KEY, ALLOWED_HOSTS,
CSRF_TRUSTED_ORIGINS, POSTGRES_*, GITHUB_*).
"""

import os

from .base import *  # noqa: F401,F403


def _env_flag(name, default="False"):
    return os.getenv(name, default).lower() in ("true", "t", "1", "yes")


DEBUG = False

# HTTPS / cookies: todos OFF por default (porta 80 sem TLS na box).
# Ligar via env quando houver terminacao TLS na borda.
SECURE_SSL_REDIRECT = _env_flag("SECURE_SSL_REDIRECT", "False")
SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", "False")
CSRF_COOKIE_SECURE = _env_flag("CSRF_COOKIE_SECURE", "False")

# HSTS: default 0 (desligado). Em prod com TLS, setar p/ 31536000 (1 ano).
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_flag(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", "False"
)
SECURE_HSTS_PRELOAD = _env_flag("SECURE_HSTS_PRELOAD", "False")

# Atras de proxy: confiar no header X-Forwarded-Proto pra detectar https
# quando o TLS termina na borda. So tem efeito se o proxy setar o header.
if _env_flag("USE_X_FORWARDED_PROTO", "False"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

USE_X_FORWARDED_HOST = _env_flag("USE_X_FORWARDED_HOST", "False")

# Clickjacking
X_FRAME_OPTIONS = "DENY"

# Em producao nao queremos CREATE_FAKE_DATA, mesmo que o env var venha ligado.
CREATE_FAKE_DATA = False
