"""
Utilitários para assinatura e verificação de tokens temporários.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from django.conf import settings
from django.core import signing

logger = logging.getLogger(__name__)


class DashboardTokenSigner:
    """
    Gerencia assinatura e verificação de tokens temporários
    para acesso a dashboards do Grafana.
    """

    def __init__(self):
        """Inicializa o signer com configurações do Django."""
        self.signer = signing.TimestampSigner(key=settings.SECRET_KEY, salt='grafana_dashboard_token')
        self.max_age = settings.GRAFANA_CONFIG.get('TOKEN_MAX_AGE', 3600)  # 1h

    def sign_token(
        self, user_id: int, dashboard_uid: str, repository_id: Optional[int] = None
    ) -> str:
        """
        Cria um token assinado para acesso ao dashboard.

        Args:
            user_id: ID do usuário
            dashboard_uid: UID do dashboard
            repository_id: ID do repositório (opcional)

        Returns:
            str: Token assinado
        """
        payload = {
            'user_id': user_id,
            'dashboard_uid': dashboard_uid,
            'repository_id': repository_id,
            'issued_at': datetime.utcnow().isoformat(),
        }

        token = self.signer.sign_object(payload)
        logger.info(f'Token assinado criado para user={user_id}, dashboard={dashboard_uid}')
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verifica e decodifica um token assinado.

        Args:
            token: Token assinado

        Returns:
            dict: Payload do token ou None se inválido/expirado
        """
        try:
            payload = self.signer.unsign_object(token, max_age=self.max_age)
            logger.debug(f'Token verificado com sucesso: {payload.get("dashboard_uid")}')
            return payload
        except signing.SignatureExpired:
            logger.warning('Token expirado')
            return None
        except signing.BadSignature:
            logger.warning('Token inválido (assinatura incorreta)')
            return None

    def get_expiration_time(self) -> datetime:
        """
        Retorna o timestamp de expiração para novos tokens.

        Returns:
            datetime: Timestamp UTC de expiração
        """
        return datetime.utcnow() + timedelta(seconds=self.max_age)


# Instância global para reutilização
dashboard_signer = DashboardTokenSigner()
