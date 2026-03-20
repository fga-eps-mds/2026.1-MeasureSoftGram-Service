from resources import calculate_subcharacteristics
from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

import utils
from organizations.models import Product, Repository
from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)
from subcharacteristics.serializers import (
    CalculatedSubCharacteristicHistorySerializer,
    LatestCalculatedSubCharacteristicSerializer,
    SubCharacteristicsCalculationsRequestSerializer,
    SupportedSubCharacteristicSerializer,
)


class SupportedSubCharacteristicModelViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset que retorna todas as subcaracterísticas suportadas pelo sistema
    """

    queryset = SupportedSubCharacteristic.objects.all()
    serializer_class = SupportedSubCharacteristicSerializer


class RepositorySubCharacteristicMixin:
    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )

    def get_queryset(self):
        repository = self.get_repository()
        qs = repository.calculated_subcharacteristics.all()
        qs = qs.values_list('subcharacteristic', flat=True).distinct()
        return SupportedSubCharacteristic.objects.filter(id__in=qs)


class LatestCalculatedSubCharacteristicModelViewSet(
    RepositorySubCharacteristicMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para recuperar o último valor calculado da subcaracterística
    """

    queryset = SupportedSubCharacteristic.objects.prefetch_related(
        'calculated_subcharacteristics',
    )
    serializer_class = LatestCalculatedSubCharacteristicSerializer


class CalculatedSubCharacteristicHistoryModelViewSet(
    RepositorySubCharacteristicMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para recuperar o histórico de subcaracterísticas calculadas
    """

    queryset = SupportedSubCharacteristic.objects.prefetch_related(
        'calculated_subcharacteristics',
    )
    serializer_class = CalculatedSubCharacteristicHistorySerializer
