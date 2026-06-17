from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from resources import calculate_tsqmi
from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from characteristics.models import SupportedCharacteristic
from measures.models import SupportedMeasure
from metrics.models import SupportedMetric
from organizations.models import Product, Repository
from organizations.mixins import UserScopedMixin
from tsqmi.models import TSQMI
from tsqmi.serializers import (
    TSQMICalculationRequestSerializer,
    TSQMISerializer,
)
from utils.exceptions import CharacteristicNotDefinedInReleaseConfigurationuration
from django.http import HttpResponse


class LatestCalculatedTSQMIViewSet(
    UserScopedMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TSQMISerializer

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
    permission_classes = []
    authentication_classes = []

    GRADE_MAP = [
        (0.80, 'A', '#4c1'),
        (0.60, 'B', '#97CA00'),
        (0.40, 'C', '#dfb317'),
        (0.20, 'D', '#fe7d37'),
        (0.00, 'E', '#e05d44'),
    ]

    BADGE_SVG_TEMPLATE = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="158" height="20">'
        '<linearGradient id="a" x2="0" y2="100%">'
        '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/>'
        '</linearGradient>'
        '<rect rx="3" width="158" height="20" fill="#555"/>'
        '<rect rx="3" x="128" width="30" height="20" fill="{color}"/>'
        '<path fill="{color}" d="M128 0h4v20h-4z"/>'
        '<rect rx="3" width="158" height="20" fill="url(#a)"/>'
        '<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,'
        'Verdana,Geneva,sans-serif" font-size="11">'
        '<text x="65" y="15" fill="#010101" fill-opacity=".3">'
        'MeasureSoftGram</text>'
        '<text x="65" y="14">MeasureSoftGram</text>'
        '<text x="143" y="15" fill="#010101" fill-opacity=".3">{grade}</text>'
        '<text x="143" y="14">{grade}</text>'
        '</g>'
        '</svg>'
    )

    BADGE_STALE_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="158" height="20">'
        '<rect rx="3" width="158" height="20" fill="#9f9f9f"/>'
        '<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,'
        'Verdana,Geneva,sans-serif" font-size="11">'
        '<text x="79" y="14">MeasureSoftGram N/A</text>'
        '</g></svg>'
    )

    def get_repository(self):
        return get_object_or_404(
            Repository,
            id=self.kwargs["repository_pk"],
            product_id=self.kwargs["product_pk"],
            product__organization_id=self.kwargs["organization_pk"],
        )

    def get_grade(self, value):
        for threshold, grade, color in self.GRADE_MAP:
            if value >= threshold:
                return grade, color
        return 'E', '#e05d44'

    def is_stale(self, tsqmi):
        """Return True if the TSQMI is older than the configured max age."""
        max_age_days = settings.BADGE_STALENESS_DAYS
        if max_age_days is None or max_age_days <= 0:
            return False
        return timezone.now() - tsqmi.created_at > timedelta(days=max_age_days)

    def list(self, request, *args, **kwargs):
        repository = self.get_repository()
        latest_tsqmi = repository.calculated_tsqmis.first()

        if latest_tsqmi is None or self.is_stale(latest_tsqmi):
            return HttpResponse(
                self.BADGE_STALE_SVG,
                content_type="image/svg+xml",
            )

        grade, color = self.get_grade(latest_tsqmi.value)
        svg = self.BADGE_SVG_TEMPLATE.format(grade=grade, color=color)
        return HttpResponse(svg, content_type="image/svg+xml")


class CalculatedTSQMIHistoryModelViewSet(
    UserScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para cadastrar as medidas coletadas
    """

    serializer_class = TSQMISerializer

    def get_queryset(self):
        repository = self.get_repository()
        return repository.calculated_tsqmis.all().reverse()
