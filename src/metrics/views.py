from rest_framework import mixins, viewsets, permissions
from rest_framework.generics import get_object_or_404

from metrics.models import CollectedMetric, SupportedMetric
from metrics.serializers import (
    CollectedMetricHistorySerializer,
    LatestCollectedMetricSerializer,
    SupportedMetricSerializer,
)
from organizations.models import Repository


class SupportedMetricModelViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset que retorna todas as métricas suportadas pelo sistema
    """

    queryset = SupportedMetric.objects.all()
    serializer_class = SupportedMetricSerializer


class RepositoryMetricsMixin:
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        repository = self.get_repository()
        serializer.save(repository=repository)

    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )

    def get_queryset(self):
        repository = self.get_repository()
        qs = repository.collected_metrics.all()
        qs = qs.values_list('metric', flat=True).distinct()
        return SupportedMetric.objects.filter(id__in=qs)


class LatestCollectedMetricModelViewSet(
    RepositoryMetricsMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para ler o valor mais recente das métricas coletadas
    """

    queryset = SupportedMetric.objects.prefetch_related('collected_metrics')

    serializer_class = LatestCollectedMetricSerializer


class CollectedMetricHistoryModelViewSet(
    RepositoryMetricsMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para ler o histórico de métricas coletadas

    TODO: Criar uma classe de paginação (
        https://www.django-rest-framework.org/api-guide/pagination/#modifying-the-pagination-style
    )
    """

    queryset = SupportedMetric.objects.prefetch_related(
        'collected_metrics',
    )
    serializer_class = CollectedMetricHistorySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['start_at'] = self.request.query_params.get('start_at')
        context['end_at'] = self.request.query_params.get('end_at')
        return context
