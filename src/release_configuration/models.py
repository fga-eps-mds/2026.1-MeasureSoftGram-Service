from django.db import models
from django.utils import timezone
from util import Checker  # util do core
from resources.constants import AGGREGATED_NORMALIZED_MEASURES_MAPPING
import utils
from characteristics.models import SupportedCharacteristic
from measures.models import SupportedMeasure
from subcharacteristics.models import SupportedSubCharacteristic
from utils.exceptions import InvalidReleaseConfigurationException


class ReleaseConfiguration(models.Model):
    """
    Classe que abstrai uma pré-configuração do modelo.

    Nessa tabela será armazenado todas as pré-configurações criadas do modelo,
    sendo que a última pré-configuração é sempre a vigente. Ou seja, as tuplas
    dessa tabela não devem ser editadas ou apagadas, somente adicionadas novas
    """

    class Meta:
        # Aqui estamos ordenando na ordem decrescente, ou seja, nos
        # querysets os registros mais recentes vem
        # primeiro (qs.first() == mais recente)
        ordering = ['-created_at']

    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=128, null=True, blank=True)
    data = models.JSONField()

    product = models.ForeignKey(
        to='organizations.Product',
        related_name='release_configuration',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f'ID: {self.id}, Name: {self.name}'

    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save para validar se a pré-configuração que
        está sendo criada ou editada é ou não válida
        """
        if self.id:
            raise ValueError("It's not allowed to edit a release-configuration")

        self.validate_measures(self.data)
        self.validate_measures_weights(self.data)

        self.validate_subcharacteristics(self.data)
        self.validate_subcharacteristics_measures_relation(self.data)
        self.validate_subcharacteristics_weights(self.data)

        self.validate_characteristics(self.data)
        self.validate_characteristics_subcharacteristics_relation(self.data)
        self.validate_characteristics_weights(self.data)
        self.validate_thresholds(self.data)

        super().save(*args, **kwargs)

    def get_measure_weight(self, measure_key: str) -> float:
        """
        Função que retorna o peso de uma medida.

        Observação: Aqui estou usando um algorítmo O(C * S * M) para
        simplificar a assinatura da função, pois caso contrário seria
        necessário passar a characteristics_key, a subcharacteristics_key e a
        measure_key. Na pior das hipóteses o C (quantidade de características)
        será 20, o S (quantidade de subcaracterísticas) será 20 e o M
        (quantidade de medidas) será 20, o que resulta em um loop de 8000
        iterações, o que não é nada.
        """
        for characteristic in self.data['characteristics']:
            for subcharacteristic in characteristic['subcharacteristics']:
                for measure in subcharacteristic['measures']:
                    if measure['key'] == measure_key:
                        return measure['weight']

        return None

    def get_subcharacteristic_weight(
        self, subcharacteristic_key: str
    ) -> float:
        for characteristic in self.data['characteristics']:
            for subcharacteristic in characteristic['subcharacteristics']:
                if subcharacteristic['key'] == subcharacteristic_key:
                    return subcharacteristic['weight']

        return None

    def get_characteristic_weight(self, characteristic_key: str) -> float:
        for characteristic in self.data['characteristics']:
            if characteristic['key'] == characteristic_key:
                return characteristic['weight']

        return None

    def get_characteristics_keys(self):
        return [charac['key'] for charac in self.data['characteristics']]

    def get_characteristics_qs(self):
        characteristics_keys = self.get_characteristics_keys()

        return SupportedCharacteristic.objects.filter(
            key__in=characteristics_keys,
        )

    def get_subcharacteristics_qs(self):
        subcharacteristics_keys = [
            subcharac['key']
            for charac in self.data['characteristics']
            for subcharac in charac['subcharacteristics']
        ]
        return SupportedSubCharacteristic.objects.filter(
            key__in=subcharacteristics_keys,
        )

    def get_measures_qs(self):
        measures_keys = [
            measure['key']
            for charac in self.data['characteristics']
            for subcharac in charac['subcharacteristics']
            for measure in subcharac['measures']
        ]
        return SupportedMeasure.objects.filter(
            key__in=measures_keys,
        )

    @staticmethod
    def validate_measures(data: dict):
        """
        Verifica se as medidas contidas no dicionário `data` são suportadas.

        Raises a `ValueError` caso alguma medida não seja suportada.
        """
        selected_measures_set = set()

        for characteristic in data['characteristics']:
            for subcharacteristic in characteristic['subcharacteristics']:
                for measure in subcharacteristic['measures']:
                    measure_key = measure['key']
                    selected_measures_set.add(measure_key)

        unsuported: str = utils.validate_entity(
            selected_measures_set,
            SupportedMeasure.has_unsupported_measures,
        )

        if unsuported:
            raise InvalidReleaseConfigurationException(
                f'The following measures are not supported: {unsuported}'
            )

    @staticmethod
    def validate_measures_weights(data: dict):
        """
        Verifica se o somatório do peso das medidas é igual a 100

        Raises a `InvalidReleaseConfigurationException` caso alguma weight não seja
        """
        for characteristic in data['characteristics']:
            for subcharacteristic in characteristic['subcharacteristics']:
                sum_of_weights: int = sum(
                    measure['weight']
                    for measure in subcharacteristic['measures']
                )

                if sum_of_weights != 100:
                    raise InvalidReleaseConfigurationException(
                        (
                            'The sum of weights of measures of subcharacteristic '
                            f"`{subcharacteristic['key']}` is not 100"
                        )
                    )

    @staticmethod
    def validate_subcharacteristics(data: dict):
        """
        Verifica se as subcharacteristics contidas no dicionário `data` são
        suportadas

        Raises a `InvalidReleaseConfigurationException` caso alguma subcharacteristic não seja
        """
        selected_subcharacteristics_set = set()

        for characteristic in data['characteristics']:
            for subcharacteristic in characteristic['subcharacteristics']:
                subcharacteristic_key = subcharacteristic['key']
                selected_subcharacteristics_set.add(subcharacteristic_key)

        unsuported: str = utils.validate_entity(
            selected_subcharacteristics_set,
            SupportedSubCharacteristic.has_unsupported_subcharacteristics,
        )

        if unsuported:
            raise InvalidReleaseConfigurationException(
                f'The following subcharacteristics are not supported: {unsuported}'
            )

    @staticmethod
    def validate_subcharacteristics_measures_relation(data: dict):
        """
        Valida se as medidas que estão relacionadas com as subcaracteristicas
        na pré-configuração são realmente relacionadas com as
        subcaracteristicas no modelo

        Raises a `InvalidReleaseConfigurationException` caso alguma medida não seja relacionada
        """

        for characteristic in data['characteristics']:
            for subcharacteristic in characteristic['subcharacteristics']:
                subchar = SupportedSubCharacteristic.objects.get(
                    key=subcharacteristic['key'],
                )

                sub_measures = {
                    measure['key'] for measure in subcharacteristic['measures']
                }

                if invalid_measures := subchar.has_unsupported_measures(
                    sub_measures
                ):
                    invalid_measures: list = [
                        f'`{key}`' for key in invalid_measures
                    ]
                    invalid_measures: str = ', '.join(invalid_measures)

                    raise InvalidReleaseConfigurationException(
                        (
                            'Failed to save release-config. It is not allowed to '
                            f'associate the measures [{invalid_measures}] with the '
                            f'subcharacteristic {subchar.key}'
                        )
                    )

    @staticmethod
    def validate_subcharacteristics_weights(data: dict):
        """
        Verifica se o somatório do peso das subcharacteristics é igual a 100

        Raises a `InvalidReleaseConfigurationException` caso alguma weight não seja
        """
        for characteristic in data['characteristics']:
            sum_of_weights: int = sum(
                subcharacteristic['weight']
                for subcharacteristic in characteristic['subcharacteristics']
            )

            if sum_of_weights != 100:
                raise InvalidReleaseConfigurationException(
                    (
                        'The sum of weights of subcharacteristics of '
                        f"characteristic `{characteristic['key']}` is not 100"
                    )
                )

    @staticmethod
    def validate_characteristics(data: dict):
        """
        Verifica se as characteristics contidas no dicionário `data` são
        suportadas

        Raises a `InvalidReleaseConfigurationException` caso alguma characteristic não seja
        """
        selected_characteristics_set = set()

        for characteristic in data['characteristics']:
            characteristic_key = characteristic['key']
            selected_characteristics_set.add(characteristic_key)

        unsuported: str = utils.validate_entity(
            selected_characteristics_set,
            SupportedCharacteristic.has_unsupported_characteristics,
        )

        if unsuported:
            raise InvalidReleaseConfigurationException(
                f'The following characteristics are not supported: {unsuported}'
            )

    @staticmethod
    def validate_characteristics_subcharacteristics_relation(data: dict):
        """
        Valida se as subcharacteristics que estão relacionadas com as
        characteristics na pré-configuração são realmente relacionadas com as
        characteristics no modelo

        Raises a `InvalidReleaseConfigurationException` caso alguma subcharacteristic não seja
        """

        for characteristic in data['characteristics']:
            charact = SupportedCharacteristic.objects.get(
                key=characteristic['key'],
            )

            charact_subcharacteristics = {
                subcharacteristic['key']
                for subcharacteristic in characteristic['subcharacteristics']
            }

            if invalid_subs := charact.has_unsupported_subcharacteristics(
                charact_subcharacteristics,
            ):
                invalid_subs: list = [f'`{key}`' for key in invalid_subs]
                invalid_subs: str = ', '.join(invalid_subs)

                raise InvalidReleaseConfigurationException(
                    (
                        'Failed to save release-config. It is not allowed to '
                        f'associate the subcharacteristics [{invalid_subs}] '
                        f'with the characteristic {charact.key}'
                    )
                )

    @staticmethod
    def validate_characteristics_weights(data: dict):
        """
        Verifica se o somatório do peso das characteristics é igual a 100

        Raises a `InvalidReleaseConfigurationException` caso alguma weight não seja
        """
        sum_of_weights: int = sum(
            characteristic['weight']
            for characteristic in data['characteristics']
        )

        if sum_of_weights != 100:
            raise InvalidReleaseConfigurationException(
                'The sum of weights of characteristics is not 100'
            )

    @staticmethod
    def validate_thresholds(data: dict):
        """
        Verifica se os thresholds estão no AGGREGATED_NORMALIZED_MEASURES_MAPPING para aquela measure.
        """

        checker_adapter = {
            'non_complex_file_density': 'non_complex_files_density',
            'test_builds': 'fast_test_builds',
            'passed_tests': 'passed_tests',
            'test_coverage': 'test_coverage',
            'commented_file_density': 'comment_files_density',
            'duplication_absense': 'absence_of_duplications',
            'ci_feedback_time': 'ci_feedback_time',
            'team_throughput': 'team_throughput',
        }

        for characteristic in data['characteristics']:
            for subcharacteristic in characteristic['subcharacteristics']:
                for measure in subcharacteristic['measures']:
                    if (
                        'min_threshold' not in measure
                        or 'max_threshold' not in measure
                    ):
                        continue
                    try:
                        Checker.check_threshold(
                            measure.get('min_threshold'),
                            measure.get('max_threshold'),
                            checker_adapter.get(measure.get('key')),
                        )
                    except Exception as e:
                        raise InvalidReleaseConfigurationException(
                            f'Invalid Threshold! {str(measure)} {str(e)}'
                        )
