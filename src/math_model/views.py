from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from math_model.services import MathModelServices
from release_configuration.serializers import ReleaseConfigurationSerializer
from utils import utils
from utils.exceptions import CalculateModelException

from .utils import parse_release_configuration


class CalculateMathModelViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet para cálculo do modelo matemático do MeasureSoftGram."""

    def create(self, request, *args, **kwargs):
        repository = utils.get_repository(
            self.kwargs['organization_pk'],
            self.kwargs['product_pk'],
            self.kwargs['repository_pk'],
        )
        product = utils.get_product(
            self.kwargs['organization_pk'],
            self.kwargs['product_pk'],
        )
        services = MathModelServices(repository, product)

        release_configuration = product.release_configuration.first()
        config_serializer = ReleaseConfigurationSerializer(release_configuration)
        char_keys, subchar_keys, measure_keys = parse_release_configuration(
            config_serializer.data,
        )

        try:
            # Fase 1: cálculo em memória — sem locks de banco.
            collected_metrics = services.build_collected_metrics(request.data)
            measures, measure_values = services.build_calculated_measures(
                measure_keys, release_configuration, collected_metrics,
            )
            subchars, subchar_values = services.build_calculated_subcharacteristics(
                subchar_keys, release_configuration, measure_values,
            )
            chars, char_values = services.build_calculated_characteristics(
                char_keys, release_configuration, subchar_values,
            )
            tsqmi = services.build_tsqmi(release_configuration, char_values)

            # Fase 2: persistência atômica — uma única transação curta.
            response = services.persist_all(
                collected_metrics, measures, subchars, chars, tsqmi,
            )
        except CalculateModelException as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(response, status=status.HTTP_201_CREATED)
