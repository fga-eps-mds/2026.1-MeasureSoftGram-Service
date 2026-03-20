from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

import utils
from characteristics.models import (
    BalanceMatrix,
    CalculatedCharacteristic,
    SupportedCharacteristic,
)


class SupportedCharacteristicSerializer(serializers.ModelSerializer):
    """
    Serializadora para uma característica suportada
    """

    class Meta:
        model = SupportedCharacteristic
        fields = (
            'id',
            'key',
            'name',
            'description',
        )


class BalanceMatrixSerializer(serializers.ModelSerializer):
    """
    Serializadora para a matriz de balanceamento
    """

    source_characteristic = SupportedCharacteristicSerializer()
    target_characteristic = SupportedCharacteristicSerializer()

    class Meta:
        model = BalanceMatrix
        fields = (
            'id',
            'source_characteristic',
            'target_characteristic',
            'relation_type',
        )

        extra_kwargs = {
            'key': {'read_only': True},
        }


class CalculatedCharacteristicSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar as características calculadas
    """

    class Meta:
        model = CalculatedCharacteristic
        fields = (
            'id',
            'characteristic_id',
            'value',
            'created_at',
        )


class LatestCalculatedCharacteristicSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar as características suportadas e seu último cálculo
    """

    latest = serializers.SerializerMethodField()

    class Meta:
        model = SupportedCharacteristic
        fields = (
            'id',
            'key',
            'name',
            'description',
            'latest',
        )

    def get_latest(self, obj: SupportedCharacteristic):
        try:
            repository = self.context['view'].get_repository()

            latest = obj.calculated_characteristics.filter(
                repository=repository
            ).first()

            return CalculatedCharacteristicSerializer(latest).data
        except SupportedCharacteristic.DoesNotExist:
            return None


class CalculatedCharacteristicHistorySerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()

    class Meta:
        model = SupportedCharacteristic
        fields = (
            'id',
            'key',
            'name',
            'description',
            'history',
        )

    def get_history(self, obj: SupportedCharacteristic):
        MAX = settings.MAXIMUM_NUMBER_OF_HISTORICAL_RECORDS

        try:
            qs = obj.calculated_characteristics.all()

            repository = self.context['view'].get_repository()
            qs = qs.filter(repository=repository)
            qs = qs.reverse()

            return CalculatedCharacteristicSerializer(
                qs[:MAX],
                many=True,
            ).data

        except CalculatedCharacteristic.DoesNotExist:
            return None


class CharacteristicsCalculationRequestSerializer(serializers.Serializer):
    """
    Serializadora usada para solicitar o cálculo de uma característica
    """

    key = serializers.CharField(max_length=255)


class CharacteristicsCalculationsRequestSerializer(serializers.Serializer):
    """
    Serializadora usada para solicitar o cálculo de várias características

    Aqui estou definindo uma lista de objetos pois é provável que no futuro
    outros parâmetros além de nome sejam necessários, e deste modo a evolução
    da API será somente a adição de novas chaves em
    CharacteristicsCalculationRequestSerializer
    """

    characteristics = serializers.ListField(
        child=CharacteristicsCalculationRequestSerializer(),
        required=True,
    )

    created_at = serializers.DateTimeField(default=timezone.now)

    def validate(self, attrs):
        """
        Valida se todas as características solicitadas são suportadas
        """
        characteristics_keys = [
            char['key'] for char in attrs['characteristics']
        ]

        unsuported_chars: str = utils.validate_entity(
            characteristics_keys,
            SupportedCharacteristic.has_unsupported_characteristics,
        )

        if unsuported_chars:
            raise serializers.ValidationError(
                (
                    'The following characteristics are '
                    f'not supported: {unsuported_chars}'
                )
            )

        return attrs
