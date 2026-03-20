from rest_framework import serializers

from characteristics.models import SupportedCharacteristic
from characteristics.serializers import SupportedCharacteristicSerializer
from measures.serializers import SupportedMeasureSerializer
from release_configuration.models import ReleaseConfiguration
from subcharacteristics.serializers import SupportedSubCharacteristicSerializer


class CharacteristicEntityRelationshipTreeSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer para a árvore de relacionamentos entre as entidades
    """

    subcharacteristics = serializers.SerializerMethodField()

    class Meta:
        model = SupportedCharacteristic
        fields = (
            'id',
            'name',
            'key',
            'description',
            'subcharacteristics',
        )

    def get_subcharacteristics(self, obj: SupportedCharacteristic):
        return SubCharacteristicEntityRelationshipTreeSerializer(
            obj.subcharacteristics.all(),
            many=True,
        ).data


class SubCharacteristicEntityRelationshipTreeSerializer(
    serializers.ModelSerializer,
):
    measures = serializers.SerializerMethodField()

    class Meta:
        model = SupportedCharacteristic
        fields = (
            'id',
            'name',
            'key',
            'description',
            'measures',
        )

    def get_measures(self, obj: SupportedCharacteristic):
        return SupportedMeasureSerializer(
            obj.measures.all(),
            many=True,
        ).data


def pre_config_to_entity_tree(pre_config: ReleaseConfiguration):
    """
    Serializadora que converte uma pré-configuração em uma árvore de entidades

    Retorna a árvore de relacionamentos entre as entidades de acordo com
    as entidades selecionadas na pre configuração.
    """

    def qs_to_dict(qs):
        return {obj.key: obj for obj in qs}

    characteristics_qs = pre_config.get_characteristics_qs()
    subcharacteristics_qs = pre_config.get_subcharacteristics_qs()
    measures_qs = pre_config.get_measures_qs()

    characteristics_dict = qs_to_dict(characteristics_qs)
    subcharacteristics_dict = qs_to_dict(subcharacteristics_qs)
    measures_dict = qs_to_dict(measures_qs)

    data = []

    for charac in pre_config.data['characteristics']:
        c_data = SupportedCharacteristicSerializer(
            characteristics_dict[charac['key']],
        ).data

        c_data['subcharacteristics'] = []

        for subcharac in charac['subcharacteristics']:
            s_data = SupportedSubCharacteristicSerializer(
                subcharacteristics_dict[subcharac['key']],
            ).data

            s_data['measures'] = []

            for measure in subcharac['measures']:
                m_data = SupportedMeasureSerializer(
                    measures_dict[measure['key']],
                ).data

                s_data['measures'].append(m_data)

            c_data['subcharacteristics'].append(s_data)

        data.append(c_data)

    return data
