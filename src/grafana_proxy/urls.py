"""
URLs para Grafana Proxy API.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import GrafanaProxyViewSet

# Router para endpoints do ViewSet
router = DefaultRouter()

# URLs customizadas (sem router para mais controle)
app_name = 'grafana_proxy'

urlpatterns = [
    path('dashboards/', GrafanaProxyViewSet.as_view({'get': 'list_dashboards'}), name='dashboards'),
    path(
        'dashboard/<str:pk>/',
        GrafanaProxyViewSet.as_view({'get': 'get_dashboard'}),
        name='dashboard',
    ),
    path('embed/<str:pk>/', GrafanaProxyViewSet.as_view({'get': 'embed_dashboard'}), name='embed'),
    path(
        'verify-token/', GrafanaProxyViewSet.as_view({'get': 'verify_token'}), name='verify-token'
    ),
]
