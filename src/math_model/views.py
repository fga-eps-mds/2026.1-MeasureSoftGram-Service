from math_model.serializer import MetricsSerializer
from rest_framework import mixins, viewsets, status
from math_model.services import MathModelServices
from rest_framework.response import Response
from utils import utils
from utils.exceptions import CalculateModelException
from .utils import parse_release_configuration
from release_configuration.serializers import ReleaseConfigurationSerializer


class CalculateMathModelViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para cálculo do modelo matematico do MeasureSoftGram
    """

    def create(self, request, *args, **kwargs):
        repository_id = self.kwargs['repository_pk']
        product_id = self.kwargs['product_pk']
        organization_id = self.kwargs['organization_pk']
        repository = utils.get_repository(organization_id, product_id, repository_id)
        product = utils.get_product(organization_id, product_id)
        services = MathModelServices(repository, product)

        release_configuration = product.release_configuration.first()
        config_serializer = ReleaseConfigurationSerializer(release_configuration)
        char_keys, subchar_keys, measure_keys = parse_release_configuration(config_serializer.data)

        response = {}
        try:
            response["metrics"] = services.collect_metrics(request.data)
            response["measures"] = services.calculate_measures(measure_keys, release_configuration)
            response["subcharacteristics"] = services.calculate_sucharacteristics(subchar_keys, release_configuration)
            response["characteristics"] = services.calculcate_characterisctics(char_keys, release_configuration)
            response["tsqmi"] = services.calculate_tsqmi(release_configuration)
        except CalculateModelException as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(response, status=status.HTTP_201_CREATED)
