from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

import utils
from measures.models import CalculatedMeasure, SupportedMeasure


class SupportedMeasureSerializer(serializers.ModelSerializer):
    """
    Serializadora para uma medida suportada
    """

    class Meta:
        model = SupportedMeasure
        fields = (
            'id',
            'key',
            'name',
            'description',
        )


class MeasureCalculationRequestSerializer(serializers.Serializer):
    """
    Serializadora usada para solicitar o cálculo de uma medida
    """

    key = serializers.CharField(max_length=255)


class MeasuresCalculationsRequestSerializer(serializers.Serializer):
    """
    Serializadora usada para solicitar o cálculo de várias medidas

    Aqui estou definindo uma lista de objetos pois é provável que no futuro
    outros parâmetros além de nome sejam necessários, e deste modo a evolução
    da API será somente a adição de novas chaves em
    MeasureCalculationRequestSerializer
    """

    measures = serializers.ListField(
        child=MeasureCalculationRequestSerializer(),
        required=True,
    )
    created_at = serializers.DateTimeField(default=timezone.now)

    def validate_measures(self, value):
        if not value:
            raise serializers.ValidationError('No measures were provided')
        return value

    def validate(self, attrs):
        """
        Valida se todas as medidas solicitadas são suportadas
        """
        measure_keys = [measure['key'] for measure in attrs['measures']]

        unsuported_measures: str = utils.validate_entity(
            measure_keys,
            SupportedMeasure.has_unsupported_measures,
        )

        if unsuported_measures:
            raise serializers.ValidationError(
                (
                    'The following measures are '
                    f'not supported: {unsuported_measures}'
                )
            )

        return attrs


class CalculatedMeasureSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar as medidas calculadas
    """

    class Meta:
        model = CalculatedMeasure
        fields = (
            'id',
            'measure_id',
            'value',
            'created_at',
        )


class LatestMeasuresCalculationsRequestSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar as medidas suportadas
    e seu último cálculo
    """

    latest = serializers.SerializerMethodField()

    class Meta:
        model = SupportedMeasure
        fields = (
            'id',
            'key',
            'name',
            'description',
            'latest',
        )

    def get_latest(self, obj: SupportedMeasure):
        try:
            repository = self.context['view'].get_repository()

            latest = obj.calculated_measures.filter(
                repository=repository
            ).first()

            return CalculatedMeasureSerializer(latest).data
        except CalculatedMeasure.DoesNotExist:
            return None


class CalculatedMeasureHistorySerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()

    class Meta:
        model = SupportedMeasure
        fields = (
            'id',
            'key',
            'name',
            'description',
            'history',
        )

    def get_history(self, obj: SupportedMeasure):
        MAX = settings.MAXIMUM_NUMBER_OF_HISTORICAL_RECORDS
        try:
            # Os últimos 10 registros criados em ordem decrescente
            qs = obj.calculated_measures.all()

            repository = self.context['view'].get_repository()
            qs = qs.filter(repository=repository)
            qs = qs.reverse()

            return CalculatedMeasureSerializer(qs[:MAX], many=True).data
        except CalculatedMeasure.DoesNotExist:
            return None
