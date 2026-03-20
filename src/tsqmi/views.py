from resources import calculate_tsqmi
from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from characteristics.models import SupportedCharacteristic
from measures.models import SupportedMeasure
from metrics.models import SupportedMetric
from organizations.models import Product, Repository
from tsqmi.models import TSQMI
from tsqmi.serializers import (
    TSQMICalculationRequestSerializer,
    TSQMISerializer,
)
from utils.exceptions import CharacteristicNotDefinedInReleaseConfigurationuration
from django.http import HttpResponse


class LatestCalculatedTSQMIViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TSQMISerializer

    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )

    def get_queryset(self):
        repository = self.get_repository()
        return repository.calculated_tsqmis.all()

    def list(self, request, *args, **kwargs):
        repository = self.get_repository()
        latest_tsqmi = repository.calculated_tsqmis.first()
        serializer = self.get_serializer(latest_tsqmi)
        return Response(serializer.data)


class LatestCalculatedTSQMIBadgeViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TSQMISerializer

    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs["repository_pk"],
            product_id=self.kwargs["product_pk"],
            product__organization_id=self.kwargs["organization_pk"],
        )

    def set_stars(self, valor):
        if 0 < valor < 0.2:
            star = 1
        elif 0.2 <= valor < 0.4:
            star = 2
        elif 0.4 <= valor < 0.6:
            star = 3
        elif 0.6 <= valor < 0.8:
            star = 4
        elif 0.8 <= valor <= 1.0:
            star = 5
        else:
            star = 6
        return star

    def list(self, request, *args, **kwargs):
        repository = self.get_repository()
        latest_tsqmi = repository.calculated_tsqmis.first()
        result = self.set_stars(latest_tsqmi.value)

        svg_data = open(f'/src/tsqmi/media/{result}stars.svg', "rb").read()
        return HttpResponse(svg_data, content_type="image/svg+xml")


class CalculatedTSQMIHistoryModelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para cadastrar as medidas coletadas
    """

    serializer_class = TSQMISerializer

    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )

    def get_queryset(self):
        repository = get_object_or_404(
            Repository,
            id=self.kwargs['repository_pk'],
            product_id=self.kwargs['product_pk'],
            product__organization_id=self.kwargs['organization_pk'],
        )
        return repository.calculated_tsqmis.all().reverse()
