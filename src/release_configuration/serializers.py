from rest_framework import serializers

from release_configuration.models import ReleaseConfiguration
from utils.exceptions import InvalidReleaseConfigurationException


class ReleaseConfigurationSerializer(serializers.ModelSerializer):
    created_config = serializers.SerializerMethodField('has_created_config')

    class Meta:
        model = ReleaseConfiguration
        fields = ('id', 'name', 'data', 'created_at', 'created_config')
        extra_kwargs = {
            'created_at': {'read_only': True},
            'created_config': {
                'read_only': True,
            },
        }

    def has_created_config(self, obj):
        return len(ReleaseConfiguration.objects.values('id')) > 1

    def validate(self, attrs):
        """
        Valida se a pré-configuração que está sendo criada é válida
        """
        if self.instance:
            raise ValueError("It's not allowed to edit a release-configuration")

        data = attrs['data']

        try:
            ReleaseConfiguration.validate_measures(data)
            ReleaseConfiguration.validate_measures_weights(data)
            ReleaseConfiguration.validate_subcharacteristics(data)
            ReleaseConfiguration.validate_subcharacteristics_measures_relation(data)
            ReleaseConfiguration.validate_subcharacteristics_weights(data)
            ReleaseConfiguration.validate_characteristics(data)
            ReleaseConfiguration.validate_characteristics_subcharacteristics_relation(
                data
            )
            ReleaseConfiguration.validate_characteristics_weights(data)

        except InvalidReleaseConfigurationException as exc:
            raise serializers.ValidationError(exc) from exc

        return attrs


class MeasureSerializer(serializers.Serializer):
    key = serializers.CharField()
    weight = serializers.IntegerField()
    min_threshold = serializers.IntegerField()
    max_threshold = serializers.IntegerField()


class SubCharacteristicSerializer(serializers.Serializer):
    key = serializers.CharField()
    weight = serializers.IntegerField()
    measures = serializers.ListField(child=MeasureSerializer())


class CharacteristicSerializer(serializers.Serializer):
    key = serializers.CharField()
    weight = serializers.IntegerField()
    subcharacteristics = serializers.ListField(child=SubCharacteristicSerializer())


class DefaultPreConfigSerializer(serializers.Serializer):
    characteristics = serializers.ListField(child=CharacteristicSerializer())
