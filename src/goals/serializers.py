from rest_framework import serializers

from characteristics.models import CalculatedCharacteristic
from goals.models import Equalizer, Goal
from release_configuration.models import ReleaseConfiguration
from accounts.models import CustomUser


class CharacteristicDeltaSerializer(serializers.Serializer):
    """
    Exemplo:
    {
        "characteristic_key": "functional_suitability",
        "delta": 10,
    }
    """

    characteristic_key = serializers.CharField(max_length=255)
    delta = serializers.IntegerField()


class AllGoalsSerializer(serializers.ModelSerializer):
    goal = serializers.SerializerMethodField()
    accomplished = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = (
            'id',
            'created_by',
            'goal',
            'accomplished',
        )

    def get_created_by(self, obj):
        user = CustomUser.objects.get(id=obj.created_by.id)
        return user.username

    def get_goal(self, obj):
        return obj.data

    def get_accomplished(self, obj):
        # FIXME: Estamos pegando apenas as 2 primeiras, pois o mesmo
        # produto pode ter várias características calculadas
        chars = (
            CalculatedCharacteristic.objects.filter(
                repository__product=obj.product,
            )
            .values('characteristic__key', 'value')
            .order_by('characteristic__id')
            .distinct('characteristic__id')
        )
        return {char['characteristic__key']: char['value'] for char in chars}


class ReleasesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = (
            'id',
            'created_by',
        )

    def get_releases(self, obj):
        return obj.data


class GoalSerializer(serializers.ModelSerializer):
    """
    Serializadora usada para serializar um Goal (meta).

    O campo changes é usado somente na criação de novos goals (metas)
    """

    changes = CharacteristicDeltaSerializer(many=True, write_only=True)
    data = serializers.SerializerMethodField()
    allow_dynamic = serializers.BooleanField(default=False)

    class Meta:
        model = Goal
        fields = (
            'id',
            'changes',
            'data',
            'allow_dynamic',
        )

    def get_data(self, obj):
        return obj.data

    def get_pre_config_characteristics(self):
        """
        Essa função retorna as características selecionadas na
        pré-configuração vigente.

        TODO: Essa função terá que mudar quando o sistema tiver mais de um
        repositório, pois será necessário fazer um fitro na tabela ReleaseConfiguration
        pelo id do repositório.
        """
        product = self.get_product()
        pre_config = product.release_configuration.first()
        return pre_config.get_characteristics_keys()

    def all_characteristics_are_defined_in_the_pre_config(self) -> bool:
        selected_characteristics_keys = set(
            self.get_pre_config_characteristics(),
        )
        changes = self.initial_data.get('changes', [])

        characteristics_keys = {
            change['characteristic_key'] for change in changes
        }

        issubset = characteristics_keys.issubset(
            selected_characteristics_keys,
        )

        return issubset

    def check_if_all_characteristics_are_defined_in_the_pre_config(
        self,
        valid_format=True,
        raise_exception=False,
    ):
        issubset = self.all_characteristics_are_defined_in_the_pre_config()

        is_valid = valid_format and issubset

        if not is_valid and raise_exception:
            raise serializers.ValidationError(
                (
                    'It is not allowed to create goals with characteristics '
                    'that were not selected in the release-configuration.'
                )
            )

        return is_valid

    def get_product(self):
        product = None

        if view := self.context.get('view', None):
            product = view.get_product()

        return product

    def is_valid(self, raise_exception=False):
        valid_format = super().is_valid(raise_exception)

        is_valid_1 = (
            self.check_if_all_characteristics_are_defined_in_the_pre_config(
                valid_format=valid_format,
                raise_exception=raise_exception,
            )
        )

        if not (is_valid_1) and raise_exception:
            raise serializers.ValidationError('The goal is not valid.')

        return is_valid_1

    def changes_to_data(self):
        """
        Essa função converte o campo changes para o formato de dados
        """
        selected_characteristics_keys = self.get_pre_config_characteristics()
        equalizer = Equalizer(selected_characteristics_keys)

        data = self.validated_data
        changes = data.get('changes', [])
        allow_dynamic = data.get('allow_dynamic', False)

        for change in changes:
            equalizer.update(
                change['characteristic_key'],
                change['delta'],
                allow_dynamic,
            )

        return equalizer.get_goal()

    def save(self, **kwargs):
        data = self.changes_to_data()
        self.validated_data.pop('changes')
        self.validated_data.pop('allow_dynamic')
        return super().save(data=data, **kwargs)
