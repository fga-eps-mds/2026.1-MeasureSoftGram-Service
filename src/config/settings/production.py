"""
Production settings — DJANGO_SETTINGS_MODULE=config.settings.production

DEBUG=False forcado. Headers de seguranca: HSTS, SSL redirect, cookies
secure-only, XFO=DENY. Backward-compatible com env vars existentes do
deploy EC2 (SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS,
POSTGRES_*, GITHUB_*).
"""

from .base import *  # noqa: F401,F403


DEBUG = False

# HTTPS / cookies
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS: 1 ano, subdomains incluidos, ready pra preload list.
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Clickjacking
X_FRAME_OPTIONS = "DENY"

# Em producao nao queremos CREATE_FAKE_DATA, mesmo que o env var venha ligado.
CREATE_FAKE_DATA = False
