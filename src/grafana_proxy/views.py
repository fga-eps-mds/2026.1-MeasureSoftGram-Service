"""
Views para proxy de dashboards do Grafana.
"""
import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from organizations.models import Repository

from .permissions import CanAccessDashboard, CanAccessProduct
from .serializers import GrafanaDashboardListSerializer, GrafanaDashboardSerializer
from .services import GrafanaAPIClient

logger = logging.getLogger(__name__)


class GrafanaProxyViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grafana_client = GrafanaAPIClient()

    @action(detail=False, methods=['get'], url_path='dashboards')
    def list_dashboards(self, request):
        """
        GET /api/v1/grafana/dashboards/
        """
        dashboards_raw = self.grafana_client.get_dashboards()

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

        dashboard_data = self.grafana_client.get_dashboard_by_uid(dashboard_uid)
        if not dashboard_data:
            return Response({'detail': 'Dashboard not found.'}, status=status.HTTP_404_NOT_FOUND)

        product_permission = CanAccessProduct()
        if not product_permission.has_permission(request, self):
            return Response(
                {'detail': 'You do not have permission to access this product.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if repository_id:
            repo_permission = CanAccessDashboard()
            if not repo_permission.has_permission(request, self):
                return Response(
                    {'detail': 'You do not have permission to access this repository.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not Repository.objects.filter(id=repository_id, product_id=product_id).exists():
                return Response(
                    {'detail': 'Repository does not belong to the specified product.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        iframe_url = self.grafana_client.build_dashboard_url(
            uid=dashboard_uid,
            product_id=int(product_id),
            repository_id=int(repository_id) if repository_id else None,
        )

        public_url = settings.GRAFANA_CONFIG['PUBLIC_URL'].rstrip('/')
        response_data = {
            'dashboard_uid': dashboard_uid,
            'title': dashboard_data['dashboard']['title'],
            'grafana_url': f'{public_url}{iframe_url}',
            'product_id': int(product_id),
            'repository_id': int(repository_id) if repository_id else None,
        }

        serializer = GrafanaDashboardSerializer(response_data)
        return Response(serializer.data)

    def _dashboard_has_repo_selector(self, dashboard_uid: str) -> bool:
        return dashboard_uid == 'hierarquia-qualidade'
