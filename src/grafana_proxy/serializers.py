"""
Serializers para respostas da API de proxy do Grafana.
"""
from rest_framework import serializers

from organizations.models import Repository


class GrafanaDashboardSerializer(serializers.Serializer):
    """
    Serializer para metadados de um dashboard do Grafana.
    """

    dashboard_uid = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    url = serializers.URLField()
    iframe_url = serializers.CharField()
    expires_at = serializers.DateTimeField()
    repository = serializers.SerializerMethodField()

    def get_repository(self, obj):
        """
        Retorna dados do repositório se disponível.
        """
        repository_id = obj.get('repository_id')
        if not repository_id:
            return None

        try:
            repo = Repository.objects.get(id=repository_id)
            return {'id': repo.id, 'name': repo.name}
        except Repository.DoesNotExist:
            return None


class GrafanaDashboardListSerializer(serializers.Serializer):
    """
    Serializer para listagem de dashboards disponíveis.
    """

    uid = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField())
    requires_repository = serializers.BooleanField()


class TokenVerifySerializer(serializers.Serializer):
    """
    Serializer para resposta de verificação de token.
    """

    valid = serializers.BooleanField()
    payload = serializers.DictField(required=False)
    time_remaining = serializers.IntegerField(required=False)
    error = serializers.CharField(required=False)
