from django.conf import settings
from django.urls import reverse_lazy
from rest_framework import serializers
from django.utils.dateparse import parse_date

from metrics.models import CollectedMetric, SupportedMetric


class SupportedMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportedMetric
        fields = ('id', 'key', 'name', 'description')


class CollectedMetricSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para o endpoint que recebe métricas coletadas.
    """

    metric_id = serializers.IntegerField(source='metric.id')

    class Meta:
        model = CollectedMetric
        fields = (
            'id',
            'metric_id',
            'value',
            'created_at',
        )
        extra_kwargs = {
            'created_at': {'read_only': True},
        }

    def validate_metric_id(self, value):
        try:
            SupportedMetric.objects.get(id=value)

        except SupportedMetric.DoesNotExist as exc:
            raise serializers.ValidationError(
                f'There is no metric with the ID {value}.'
                'See the IDs of the metrics supported in the API in the '
                'endpoint: ' + reverse_lazy('service:supported-metrics-list')
            ) from exc

        return value

    def create(self, validated_data):
        metric_id = validated_data['metric']['id']
        metric = SupportedMetric.objects.get(id=metric_id)
        validated_data['metric'] = metric
        return super().create(validated_data)


class LatestCollectedMetricSerializer(serializers.ModelSerializer):
    """
    Serializadora que retorna o dado mais recente de uma determinada métrica.
    """

    latest = serializers.SerializerMethodField()

    class Meta:
        model = SupportedMetric
        fields = (
            'id',
            'key',
            'name',
            'description',
            'latest',
        )

    def get_latest(self, obj: SupportedMetric):
        try:
            repository = self.context['view'].get_repository()

            latest = obj.collected_metrics.filter(
                repository=repository
            ).first()

            return CollectedMetricSerializer(latest).data
        except CollectedMetric.DoesNotExist:
            return None


class CollectedMetricHistorySerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()

    class Meta:
        model = SupportedMetric
        fields = (
            'id',
            'key',
            'name',
            'description',
            'history',
        )

    def get_history(self, obj: SupportedMetric):
        MAX = settings.MAXIMUM_NUMBER_OF_HISTORICAL_RECORDS
        start_at = self.context.get('start_at')
        end_at = self.context.get('end_at')

        # Parse dates
        start_date = parse_date(start_at) if start_at else None
        end_date = parse_date(end_at) if end_at else None
        try:
            # Os últimos MAX registros criados em ordem decrescente
            qs = obj.collected_metrics.all()

            if start_date:
                qs = qs.filter(created_at__gte=start_date)
            if end_date:
                qs = qs.filter(created_at__lte=end_date)

            repository = self.context['view'].get_repository()
            qs = qs.filter(repository=repository)
            qs = qs.reverse()

            return CollectedMetricSerializer(qs[:MAX], many=True).data

        except SupportedMetric.DoesNotExist:
            return None
