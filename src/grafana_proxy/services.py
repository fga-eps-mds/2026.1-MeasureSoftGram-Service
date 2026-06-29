"""
Cliente para comunicação com a API REST do Grafana.
"""
import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GrafanaAPIClient:
    """
    Cliente HTTP para interagir com a API do Grafana.

    Responsável por:
    - Buscar dashboards disponíveis
    - Obter metadados de dashboards específicos
    - Construir URLs de acesso aos dashboards
    """

    def __init__(self):
        """Inicializa o cliente com configurações do settings."""
        self.base_url = settings.GRAFANA_CONFIG['BASE_URL']
        self.auth = (
            settings.GRAFANA_CONFIG['USERNAME'],
            settings.GRAFANA_CONFIG['PASSWORD'],
        )
        self.timeout = settings.GRAFANA_CONFIG.get('TIMEOUT', 10)

    def get_dashboards(self, tag: str = 'measuresoftgram') -> List[Dict[str, Any]]:
        """
        Lista todos os dashboards com a tag especificada.

        Args:
            tag: Tag para filtrar dashboards (default: 'measuresoftgram')

        Returns:
            list: Lista de dashboards com uid, title, tags, etc.
        """
        url = f'{self.base_url}/api/search'
        params = {'tag': tag, 'type': 'dash-db'}

        try:
            response = requests.get(url, auth=self.auth, params=params, timeout=self.timeout)
            response.raise_for_status()
            dashboards = response.json()
            logger.info(f'Encontrados {len(dashboards)} dashboards com tag "{tag}"')
            return dashboards
        except requests.RequestException as e:
            logger.error(f'Erro ao buscar dashboards do Grafana: {e}')
            return []

    def get_dashboard_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Busca um dashboard específico pelo UID.

        Args:
            uid: UID do dashboard (ex: 'saude-qualidade-repo')

        Returns:
            dict: Dados completos do dashboard ou None se não encontrado
        """
        url = f'{self.base_url}/api/dashboards/uid/{uid}'

        try:
            response = requests.get(url, auth=self.auth, timeout=self.timeout)
            response.raise_for_status()
            dashboard_data = response.json()
            logger.info(f'Dashboard {uid} encontrado: {dashboard_data.get("meta", {}).get("slug")}')
            return dashboard_data
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f'Dashboard {uid} não encontrado')
                return None
            logger.error(f'Erro HTTP ao buscar dashboard {uid}: {e}')
            return None
        except requests.RequestException as e:
            logger.error(f'Erro ao buscar dashboard {uid}: {e}')
            return None

    def build_dashboard_url(
        self,
        uid: str,
        repository_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        product_id: Optional[int] = None,
        kiosk: bool = True,
        theme: str = 'light',
    ) -> str:
        """
        Constrói a URL de acesso ao dashboard do Grafana.

        Args:
            uid: UID do dashboard
            repository_id: ID do repositório (para variáveis)
            organization_id: ID da organização (para variáveis)
            product_id: ID do produto (para variáveis)
            kiosk: Modo kiosk (sem menu/header)
            theme: Tema (light ou dark)

        Returns:
            str: URL relativa do dashboard
        """
        # Busca metadados para pegar o slug
        dashboard_data = self.get_dashboard_by_uid(uid)
        if not dashboard_data:
            # Fallback: usa o UID como slug
            slug = uid
        else:
            slug = dashboard_data.get('meta', {}).get('slug', uid)

        url = f'/d/{uid}/{slug}?orgId=1'

        # Adiciona variáveis de filtro
        if repository_id:
            url += f'&var-repository={repository_id}'
        if organization_id:
            url += f'&var-organization={organization_id}'
        if product_id:
            url += f'&var-product={product_id}'

        # Modo kiosk (remove menu, header e controles de painel)
        if kiosk:
            url += '&kiosk'

        # Tema
        url += f'&theme={theme}'

        logger.debug(f'URL construída para dashboard {uid}: {url}')
        return url

    def proxy_dashboard(self, dashboard_url: str) -> Optional[requests.Response]:
        """
        Faz proxy reverso para o Grafana e retorna a resposta completa.

        Args:
            dashboard_url: URL relativa do dashboard (ex: /d/xyz/...)

        Returns:
            Response: Resposta HTTP do Grafana ou None em caso de erro
        """
        full_url = f'{self.base_url}{dashboard_url}'

        try:
            response = requests.get(full_url, auth=self.auth, timeout=self.timeout)
            response.raise_for_status()
            logger.info(f'Proxy bem-sucedido para {dashboard_url}')
            return response
        except requests.RequestException as e:
            logger.error(f'Erro ao fazer proxy para {dashboard_url}: {e}')
            return None
