"""
Serializers para respostas da API de proxy do Grafana.
"""
from rest_framework import serializers

from organizations.models import Repository


class GrafanaDashboardSerializer(serializers.Serializer):
    dashboard_uid = serializers.CharField()
    title = serializers.CharField()
    grafana_url = serializers.URLField()
    product_id = serializers.IntegerField()
    repository = serializers.SerializerMethodField()

    def get_repository(self, obj):
        repository_id = obj.get('repository_id')
        if not repository_id:
            return None
        try:
            repo = Repository.objects.get(id=repository_id)
            return {'id': repo.id, 'name': repo.name}
        except Repository.DoesNotExist:
            return None


class GrafanaDashboardListSerializer(serializers.Serializer):
    uid = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField())
    has_repo_selector = serializers.BooleanField()
