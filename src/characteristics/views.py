from resources import calculate_characteristics
from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from characteristics.models import (
    BalanceMatrix,
    CalculatedCharacteristic,
    SupportedCharacteristic,
)
from characteristics.serializers import (
    BalanceMatrixSerializer,
    CalculatedCharacteristicHistorySerializer,
    CharacteristicsCalculationsRequestSerializer,
    LatestCalculatedCharacteristicSerializer,
    SupportedCharacteristicSerializer,
)
from organizations.models import Product, Repository
from release_configuration.models import ReleaseConfiguration
from utils.exceptions import SubCharacteristicNotDefinedInReleaseConfigurationuration


class CalculateCharacteristicViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CharacteristicsCalculationsRequestSerializer
    queryset = SupportedCharacteristic.objects.all()

    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )

    def get_product(self):
        return get_object_or_404(
            Product,
            id=self.kwargs['product_pk'],
            organization_id=self.kwargs['organization_pk'],
        )


class SupportedCharacteristicModelViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset que retorna todas as características suportadas pelo sistema
    """

    queryset = SupportedCharacteristic.objects.all()
    serializer_class = SupportedCharacteristicSerializer


class BalanceMatrixViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = BalanceMatrix.objects.all()
    serializer_class = BalanceMatrixSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        result = {}
        for balance_matrix in queryset:
            source_key = balance_matrix.source_characteristic.key
            target_key = balance_matrix.target_characteristic.key
            relation_type = balance_matrix.relation_type

            if source_key not in result:
                result[source_key] = {'+': [], '-': []}

            result[source_key][relation_type].append(target_key)

        data = {
            'count': len(result),
            'next': None,
            'previous': None,
            'result': result,
        }
        return Response(data, status=status.HTTP_200_OK)


class RepositoryCharacteristicMixin:
    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )

    def get_queryset(self):
        repository = self.get_repository()
        qs = repository.calculated_characteristics.all()
        qs = qs.values_list('characteristic', flat=True).distinct()
        return SupportedCharacteristic.objects.filter(id__in=qs)


class LatestCalculatedCharacteristicModelViewSet(
    RepositoryCharacteristicMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para recuperar o último valor calculado da característica
    """

    queryset = SupportedCharacteristic.objects.prefetch_related(
        'calculated_characteristics'
    )
    serializer_class = LatestCalculatedCharacteristicSerializer

    def get_queryset(self):
        repository = get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )
        qs = repository.calculated_characteristics.all()
        qs = qs.values_list('characteristic', flat=True).distinct()
        return SupportedCharacteristic.objects.filter(id__in=qs)


class CalculatedCharacteristicHistoryModelViewSet(
    RepositoryCharacteristicMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para recuperar o histórico de características calculadas
    """

    queryset = SupportedCharacteristic.objects.prefetch_related(
        'calculated_characteristics'
    )
    serializer_class = CalculatedCharacteristicHistorySerializer
