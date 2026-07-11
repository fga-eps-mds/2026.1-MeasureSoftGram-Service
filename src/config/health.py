"""Endpoint de saude (/health/) do container service.

View leve, sem DRF e sem autenticacao: responde 200 quando a aplicacao
esta de pe e o banco responde, e 503 quando o banco esta indisponivel.
Consumida pelo healthcheck do container `service` no docker-compose (curl).
"""

from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """Liveness/readiness: 200 se o banco responde, 503 caso contrario."""
    db_ok = True
    try:
        connections["default"].cursor()
    except OperationalError:
        db_ok = False

    payload = {
        "status": "ok" if db_ok else "unhealthy",
        "database": "ok" if db_ok else "down",
    }
    return JsonResponse(payload, status=200 if db_ok else 503)
