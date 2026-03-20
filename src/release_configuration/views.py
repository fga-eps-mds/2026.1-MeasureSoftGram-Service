from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from organizations.models import Product
from release_configuration.models import ReleaseConfiguration
from measures.models import SupportedMeasure
from release_configuration.serializers import ReleaseConfigurationSerializer, DefaultPreConfigSerializer
from staticfiles import SUPPORTED_MEASURES

from utils import staticfiles


class CurrentReleaseConfigModelViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ReleaseConfiguration.objects.all()
    serializer_class = ReleaseConfigurationSerializer

    def get_product(self):
        return get_object_or_404(
            Product,
            id=self.kwargs["product_pk"],
        )

    def list(self, request, *args, **kwargs):
        # first() == mais recente == pre configuração atual
        product = self.get_product()
        latest_pre_config = product.release_configuration.first()
        serializer = ReleaseConfigurationSerializer(latest_pre_config)
        return Response(serializer.data, status.HTTP_200_OK)


class DefaultPreConfigModelViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ReleaseConfiguration.objects.all()
    serializer_class = ReleaseConfigurationSerializer

    def get_product(self):
        return get_object_or_404(
            Product,
            id=self.kwargs["product_pk"],
        )

    def list(self, request, *args, **kwargs):
        pre_config = staticfiles.DEFAULT_PRE_CONFIG
        serializer = DefaultPreConfigSerializer(pre_config)
        return Response(serializer.data, status.HTTP_200_OK)


class CreateReleaseConfigModelViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReleaseConfigurationSerializer
    queryset = ReleaseConfiguration.objects.all()

    def get_product(self):
        return get_object_or_404(
            Product,
            id=self.kwargs["product_pk"],
        )

    def perform_create(self, serializer):
        product = self.get_product()
        serializer.save(product=product)

    def create(self, request, *args, **kwargs):
        data_to_add_metrics = request.data

        for characteristic in data_to_add_metrics["data"]["characteristics"]:
            for subcharacteristic in characteristic["subcharacteristics"]:
                for measure in subcharacteristic["measures"]:
                    metrics_list = [
                        sup_measure[measure["key"]]["metrics"]
                        for sup_measure in SUPPORTED_MEASURES
                        if measure["key"] in sup_measure
                    ]
                    measure.update(
                        {
                            "metrics": [
                                {"key": metric}
                                for metrics in metrics_list
                                for metric in metrics
                            ]
                        }
                    )

        serializer = self.get_serializer(data=data_to_add_metrics)
        serializer.is_valid(raise_exception=True)
        product = self.get_product()
        current_release_configuration = product.release_configuration.first()
        if data_to_add_metrics == current_release_configuration.data:
            return Response(data_to_add_metrics, status=status.HTTP_200_OK)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
