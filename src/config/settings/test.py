"""
Test settings — DJANGO_SETTINGS_MODULE=config.settings.test

DEBUG desligado, banco isolado (sufixo _test), hasher rapido,
APScheduler desligado pra nao subir o cron job em testes.
"""

from .base import *  # noqa: F401,F403
from .base import DATABASES, LOGGING


DEBUG = False

DATABASES["default"]["NAME"] = f"{DATABASES['default']['NAME']}_test"

# Hasher rapido — testes com user nao precisam do PBKDF2 default (lento).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Nao registra o job cron de releases.
SCHEDULER_AUTOSTART = False

# Em testes: nao popular fake data; cada teste usa fixtures proprios.
CREATE_FAKE_DATA = False

# Logging silencioso em test.
LOGGING["loggers"]["django"]["level"] = "WARNING"
