from rest_framework import serializers

from characteristics.models import SupportedCharacteristic
from characteristics.serializers import SupportedCharacteristicSerializer
from measures.serializers import SupportedMeasureSerializer
from release_configuration.models import ReleaseConfiguration
from metrics.serializers import CollectedMetricSerializer
from characteristics.serializers import CalculatedCharacteristicSerializer
from subcharacteristics.serializers import CalculatedSubCharacteristicSerializer
from measures.serializers import CalculatedMeasureSerializer
from tsqmi.serializers import TSQMISerializer
from subcharacteristics.serializers import SupportedSubCharacteristicSerializer


class GithubJSONSerializer(serializers.Serializer):
    metrics = serializers.DictField()


class SonarQubeJSONSerializer(serializers.Serializer):
    """
    Serializer for SonarQube JSON data.
    """

    paging = serializers.DictField()
    baseComponent = serializers.DictField()
    components = serializers.ListField()


class MetricsSerializer(serializers.Serializer):
    sonarqube = SonarQubeJSONSerializer()
    github = serializers.DictField()


class CalculateResponseSerializer(serializers.Serializer):
    tsqmi = TSQMISerializer
    metrics = CollectedMetricSerializer(many=True)
    measures = CalculatedMeasureSerializer(many=True)
    subcharacteristics = CalculatedSubCharacteristicSerializer(many=True)
    characteristics = CalculatedCharacteristicSerializer(many=True)
    tsqmi = TSQMISerializer()
