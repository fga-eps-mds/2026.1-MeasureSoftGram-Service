"""
App configuration for Grafana Proxy.
"""
from django.apps import AppConfig


class GrafanaProxyConfig(AppConfig):
    """Configuration for the grafana_proxy app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grafana_proxy'
    verbose_name = 'Grafana Proxy'
