from django.utils import timezone
from rest_framework import serializers

from tsqmi.models import TSQMI


class TSQMISerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar as medidas calculadas
    """

    class Meta:
        model = TSQMI
        fields = (
            'id',
            'value',
            'created_at',
        )
        read_only_fields = (
            'id',
            'value',
        )


class TSQMICalculationRequestSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField(default=timezone.now)
