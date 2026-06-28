"""
Views para proxy de dashboards do Grafana.
"""
import logging

import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from organizations.models import Product, Repository

from .permissions import CanAccessDashboard, CanAccessProduct
from .serializers import (
    GrafanaDashboardListSerializer,
    GrafanaDashboardSerializer,
    TokenVerifySerializer,
)
from .services import GrafanaAPIClient
from .utils import dashboard_signer

logger = logging.getLogger(__name__)


class GrafanaProxyViewSet(viewsets.ViewSet):
    """
    ViewSet para proxy de dashboards do Grafana.

    Endpoints:
    - GET /dashboards/ - Lista dashboards disponíveis
    - GET /dashboard/{uid}/ - Obtém URL assinada para dashboard
    - GET /embed/{uid}/ - Renderiza dashboard (proxy reverso)
    - GET /verify-token/ - Verifica validade de um token
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Permite acesso público ao endpoint embed.
        """
        if self.action == 'embed_dashboard':
            return [AllowAny()]
        return super().get_permissions()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grafana_client = GrafanaAPIClient()

    @action(detail=False, methods=['get'], url_path='dashboards')
    def list_dashboards(self, request):
        """
        Lista todos os dashboards disponíveis.

        GET /api/v1/grafana/dashboards/
        """
        dashboards_raw = self.grafana_client.get_dashboards()

        # Mapeia dashboards com metadados adicionais
        dashboards = []
        for dash in dashboards_raw:
            dashboards.append(
                {
                    'uid': dash['uid'],
                    'title': dash['title'],
                    'description': dash.get('description', ''),
                    'tags': dash.get('tags', []),
                    'has_repo_selector': self._dashboard_has_repo_selector(dash['uid']),
                }
            )

        serializer = GrafanaDashboardListSerializer(dashboards, many=True)
        return Response({'count': len(dashboards), 'results': serializer.data})

    @action(detail=True, methods=['get'], url_path='dashboard')
    def get_dashboard(self, request, pk=None):
        """
        Obtém URL assinada para acessar um dashboard específico.

        GET /api/v1/grafana/dashboard/{uid}/?product_id=3
        GET /api/v1/grafana/dashboard/{uid}/?product_id=3&repository_id=6
        """
        dashboard_uid = pk
        product_id = request.query_params.get('product_id')
        repository_id = request.query_params.get('repository_id')

        if not product_id:
            return Response(
                {'detail': 'product_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Valida que o dashboard existe
        dashboard_data = self.grafana_client.get_dashboard_by_uid(dashboard_uid)
        if not dashboard_data:
            return Response({'detail': 'Dashboard not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Valida acesso ao produto
        product_permission = CanAccessProduct()
        if not product_permission.has_permission(request, self):
            return Response(
                {'detail': 'You do not have permission to access this product.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Valida acesso ao repositório (quando fornecido)
        if repository_id:
            repo_permission = CanAccessDashboard()
            if not repo_permission.has_permission(request, self):
                return Response(
                    {'detail': 'You do not have permission to access this repository.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Garante que o repositório pertence ao produto informado
            if not Repository.objects.filter(
                id=repository_id, product_id=product_id
            ).exists():
                return Response(
                    {'detail': 'Repository does not belong to the specified product.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Gera token assinado
        signed_token = dashboard_signer.sign_token(
            user_id=request.user.id,
            dashboard_uid=dashboard_uid,
            product_id=int(product_id),
            repository_id=int(repository_id) if repository_id else None,
        )

        # Constrói URLs
        base_url = request.build_absolute_uri('/')[:-1]
        iframe_url = self.grafana_client.build_dashboard_url(
            uid=dashboard_uid,
            product_id=int(product_id),
            repository_id=int(repository_id) if repository_id else None,
        )

        grafana_direct_url = f'http://localhost:5000{iframe_url}'

        response_data = {
            'dashboard_uid': dashboard_uid,
            'title': dashboard_data['dashboard']['title'],
            'description': dashboard_data['meta'].get('description', ''),
            'url': f'{base_url}/api/v1/grafana/embed/{dashboard_uid}/?token={signed_token}',
            'iframe_url': iframe_url,
            'grafana_url': grafana_direct_url,
            'expires_at': dashboard_signer.get_expiration_time(),
            'product_id': int(product_id),
            'repository_id': int(repository_id) if repository_id else None,
        }

        serializer = GrafanaDashboardSerializer(response_data)
        return Response(serializer.data)

    @xframe_options_exempt
    @action(detail=True, methods=['get'], url_path='embed', permission_classes=[AllowAny])
    def embed_dashboard(self, request, pk=None):
        """
        Retorna URL direta do Grafana sem autenticação (anônimo).

        Este endpoint usa autenticação via token assinado na URL,
        não requer header Authorization.

        GET /api/v1/grafana/embed/{uid}/?token={signed_token}&repository_id=6
        """
        from django.shortcuts import redirect

        dashboard_uid = pk
        signed_token = request.query_params.get('token')

        if not signed_token:
            return Response({'detail': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verifica token
        payload = dashboard_signer.verify_token(signed_token)
        if not payload:
            return Response(
                {'detail': 'Invalid or expired token.'}, status=status.HTTP_403_FORBIDDEN
            )

        # Valida que o token é para este dashboard
        if payload['dashboard_uid'] != dashboard_uid:
            return Response(
                {'detail': 'Token is not valid for this dashboard.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Constrói URL do Grafana com filtros de produto e repositório
        iframe_url = self.grafana_client.build_dashboard_url(
            uid=dashboard_uid,
            product_id=payload.get('product_id'),
            repository_id=payload.get('repository_id'),
        )

        grafana_url = f"http://localhost:5000{iframe_url}"
        return redirect(grafana_url)

    @action(detail=False, methods=['get'], url_path='verify-token')
    def verify_token(self, request):
        """
        Verifica validade de um token assinado (debug).

        GET /api/v1/grafana/verify-token/?token={signed_token}
        """
        signed_token = request.query_params.get('token')

        if not signed_token:
            return Response({'detail': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        payload = dashboard_signer.verify_token(signed_token)

        if not payload:
            serializer = TokenVerifySerializer({'valid': False, 'error': 'Invalid or expired token'})
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Calcula tempo restante
        from datetime import datetime

        issued_at = datetime.fromisoformat(payload['issued_at'])
        max_age = dashboard_signer.max_age
        elapsed = (datetime.utcnow() - issued_at).total_seconds()
        time_remaining = int(max_age - elapsed)

        serializer = TokenVerifySerializer({'valid': True, 'payload': payload, 'time_remaining': time_remaining})
        return Response(serializer.data)

    def _dashboard_has_repo_selector(self, dashboard_uid: str) -> bool:
        """
        Indica se o dashboard expõe um seletor de repositório na UI do Grafana.
        Usado para informar o frontend se deve exibir um pre-seletor de repositório.
        """
        dashboards_with_repo_selector = [
            'dashboard-evolucao',
            'dashboard-saude-qualidade-repositorio',
            'dashboard-ecg-tsqmi',
        ]
        return any(uid in dashboard_uid for uid in dashboards_with_repo_selector)
