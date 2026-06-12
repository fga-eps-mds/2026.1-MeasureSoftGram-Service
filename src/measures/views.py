from resources import calculate_measures
from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from measures.models import CalculatedMeasure, SupportedMeasure
from measures.serializers import (
    CalculatedMeasureHistorySerializer,
    LatestMeasuresCalculationsRequestSerializer,
    MeasuresCalculationsRequestSerializer,
    SupportedMeasureSerializer,
)
from organizations.models import Product, Repository
from organizations.mixins import UserScopedMixin


class CalculateMeasuresViewSet(
    UserScopedMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoint que ativa o mecanismo de cálculo das medidas
    """

    serializer_class = MeasuresCalculationsRequestSerializer
    queryset = CalculatedMeasure.objects.all()


class SupportedMeasureModelViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset que retorna todas as medidas suportadas pelo sistema
    """

    queryset = SupportedMeasure.objects.all()
    serializer_class = SupportedMeasureSerializer


class RepositoryMeasuresMixin(UserScopedMixin):
    def get_queryset(self):
        repository = self.get_repository()
        qs = repository.calculated_measures.all()
        qs = qs.values_list('measure', flat=True).distinct()
        return SupportedMeasure.objects.filter(id__in=qs)


class LatestCalculatedMeasureModelViewSet(
    RepositoryMeasuresMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para cadastrar as medidas coletadas
    """

    queryset = SupportedMeasure.objects.prefetch_related(
        'calculated_measures',
    )
    serializer_class = LatestMeasuresCalculationsRequestSerializer


class CalculatedMeasureHistoryModelViewSet(
    RepositoryMeasuresMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para ler o histórico de medidas coletadas
    TODO: Criar uma classe de paginação (
        https://www.django-rest-framework.org/api-guide/pagination/#modifying-the-pagination-style
    )
    """

    queryset = SupportedMeasure.objects.prefetch_related(
        'calculated_measures',
    )
    serializer_class = CalculatedMeasureHistorySerializer

