from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

import utils
from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)


class SupportedSubCharacteristicSerializer(serializers.ModelSerializer):
    """
    Serializadora para uma subcaracterística suportada
    """

    class Meta:
        model = SupportedSubCharacteristic
        fields = (
            'id',
            'key',
            'name',
            'description',
        )


class CalculatedSubCharacteristicSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar as subcaracterísticas calculadas
    """

    class Meta:
        model = CalculatedSubCharacteristic
        fields = (
            'id',
            'subcharacteristic_id',
            'value',
            'created_at',
        )


class LatestCalculatedSubCharacteristicSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar as subcaracterísticas suportadas e seu último cálculo
    """

    latest = serializers.SerializerMethodField()

    class Meta:
        model = SupportedSubCharacteristic
        fields = (
            'id',
            'key',
            'name',
            'description',
            'latest',
        )

    def get_latest(self, obj: SupportedSubCharacteristic):
        try:
            repository = self.context['view'].get_repository()

            latest = obj.calculated_subcharacteristics.filter(
                repository=repository
            ).first()

            return CalculatedSubCharacteristicSerializer(latest).data
        except SupportedSubCharacteristic.DoesNotExist:
            return None


class CalculatedSubCharacteristicHistorySerializer(
    serializers.ModelSerializer
):
    history = serializers.SerializerMethodField()

    class Meta:
        model = SupportedSubCharacteristic
        fields = (
            'id',
            'key',
            'name',
            'description',
            'history',
        )

    def get_history(self, obj: SupportedSubCharacteristic):
        MAX = settings.MAXIMUM_NUMBER_OF_HISTORICAL_RECORDS
        try:
            qs = obj.calculated_subcharacteristics.all()

            repository = self.context['view'].get_repository()
            qs = qs.filter(repository=repository)
            qs = qs.reverse()

            return CalculatedSubCharacteristicSerializer(
                qs[:MAX],
                many=True,
            ).data
        except CalculatedSubCharacteristic.DoesNotExist:
            return None


class SubCharacteristicsCalculationRequestSerializer(serializers.Serializer):
    """
    Serializadora usada para solicitar o cálculo de uma subcaracterística
    """

    key = serializers.CharField(max_length=255)


class SubCharacteristicsCalculationsRequestSerializer(serializers.Serializer):
    """
    Serializadora usada para solicitar o cálculo de várias subcaracterísticas

    Aqui estou definindo uma lista de objetos pois é provável que no futuro
    outros parâmetros além de nome sejam necessários, e deste modo a evolução
    da API será somente a adição de novas chaves em
    SubCharacteristicsCalculationRequestSerializer
    """

    subcharacteristics = serializers.ListField(
        child=SubCharacteristicsCalculationRequestSerializer(),
        required=True,
    )

    created_at = serializers.DateTimeField(default=timezone.now)

    def validate(self, attrs):
        """
        Valida se todas as subcaracterísticas solicitadas são suportadas
        """
        subcharacteristics_keys = [
            subchar['key'] for subchar in attrs['subcharacteristics']
        ]

        unsuported_subchars: str = utils.validate_entity(
            subcharacteristics_keys,
            SupportedSubCharacteristic.has_unsupported_subcharacteristics,
        )

        if unsuported_subchars:
            raise serializers.ValidationError(
                (
                    'The following subcharacteristics are '
                    f'not supported: {unsuported_subchars}'
                )
            )

        return attrs
