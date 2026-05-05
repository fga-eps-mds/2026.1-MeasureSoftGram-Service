"""
Testes unitários do MathModelServices.

Após o refactor "calcula em memória → persiste no fim", o service
expõe métodos build_* que recebem dados de camadas anteriores em
memória (não buscam no banco) e retornam instâncias não persistidas.
A persistência mora em persist_all dentro de transaction.atomic.

Testes de integração end-to-end do endpoint vivem em
test_atomicity_smoke.py.
"""
from freezegun import freeze_time

from utils.tests import APITestCaseExpanded
from utils import staticfiles
from release_configuration.models import ReleaseConfiguration
from metrics.models import SupportedMetric, CollectedMetric
from measures.models import CalculatedMeasure, SupportedMeasure
from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)
from characteristics.models import (
    CalculatedCharacteristic,
    SupportedCharacteristic,
)
from tsqmi.models import TSQMI
from math_model.services import MathModelServices
from math_model import utils


@freeze_time("2024-09-08 20:00:00")
class MathModelServicesTest(APITestCaseExpanded):
    def setUp(self):
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        ReleaseConfiguration.objects.get_or_create(
            name='Default pre-config',
            data=staticfiles.DEFAULT_PRE_CONFIG,
            product=self.product,
        )
        self.release_config = self.product.release_configuration.first()
        self.services = MathModelServices(self.repository, self.product)

    def _build_collected_metrics_for_all_measures(self):
        """Cria CollectedMetric (não persistidos) cobrindo as 14 métricas
        que alimentam as 8 medidas do DEFAULT_PRE_CONFIG."""
        metrics = []
        listed_fil = [
            'coverage', 'complexity', 'functions',
            'comment_lines_density', 'duplicated_lines_density',
        ]
        uts = ['test_execution_time', 'tests']
        trk = ['test_failures', 'test_errors']
        github = [
            'total_issues', 'resolved_issues',
            'sum_ci_feedback_times', 'total_builds',
        ]

        for keys, qualifier in [(listed_fil, 'FIL'), (uts, 'UTS'), (trk, 'TRK')]:
            for sm in SupportedMetric.objects.filter(key__in=keys):
                # 2 valores cada — necessário pra que listas cheguem
                # ao msgram-core como list (não desempacotadas).
                metrics.append(CollectedMetric(
                    value=0.1, metric=sm, repository=self.repository,
                    qualifier=qualifier,
                ))
                metrics.append(CollectedMetric(
                    value=0.2, metric=sm, repository=self.repository,
                    qualifier=qualifier,
                ))

        for sm in SupportedMetric.objects.filter(key__in=github):
            metrics.append(CollectedMetric(
                value=1, metric=sm, repository=self.repository,
                qualifier='TRK',
            ))

        return metrics

    def test_if_parse_release_config(self):
        from release_configuration.serializers import ReleaseConfigurationSerializer
        config_serializer = ReleaseConfigurationSerializer(self.release_config)
        char_keys, subchar_keys, measure_keys = utils.parse_release_configuration(
            config_serializer.data,
        )
        assert char_keys == [
            'reliability', 'maintainability', 'functional_suitability',
        ]
        assert subchar_keys == [
            'testing_status', 'maturity', 'modifiability',
            'functional_completeness',
        ]
        assert measure_keys == [
            'passed_tests', 'test_builds', 'test_coverage',
            'ci_feedback_time', 'non_complex_file_density',
            'commented_file_density', 'duplication_absense', 'team_throughput',
        ]

    def test_build_calculated_measures_returns_instances_and_values(self):
        """build_calculated_measures retorna instâncias não persistidas
        + dict {key: value} para alimentar a próxima camada."""
        collected = self._build_collected_metrics_for_all_measures()
        measure_keys = [m.key for m in SupportedMeasure.objects.all()]

        instances, values = self.services.build_calculated_measures(
            measure_keys, self.release_config, collected,
        )

        # Não persistiu nada
        assert CalculatedMeasure.objects.count() == 0
        # Todas as 8 medidas foram calculadas
        assert len(instances) == 8
        assert all(isinstance(i, CalculatedMeasure) for i in instances)
        assert all(i.pk is None for i in instances)
        # Dict tem as mesmas keys, valores são floats
        assert set(values.keys()) == set(measure_keys)
        assert all(isinstance(v, float) for v in values.values())

    def test_build_calculated_subcharacteristics_uses_in_memory_values(self):
        measure_values = {
            m.key: 0.1 for m in SupportedMeasure.objects.all()
        }
        subchar_keys = [
            s.key for s in self.release_config.get_subcharacteristics_qs()
        ]

        instances, values = self.services.build_calculated_subcharacteristics(
            subchar_keys, self.release_config, measure_values,
        )

        assert CalculatedSubCharacteristic.objects.count() == 0
        assert len(instances) == len(subchar_keys)
        assert all(isinstance(i, CalculatedSubCharacteristic) for i in instances)
        assert all(i.pk is None for i in instances)
        assert set(values.keys()) == set(subchar_keys)

    def test_build_calculated_characteristics_uses_in_memory_values(self):
        subchar_values = {
            s.key: 0.1 for s in SupportedSubCharacteristic.objects.all()
        }
        char_keys = [
            c.key for c in self.release_config.get_characteristics_qs()
        ]

        instances, values = self.services.build_calculated_characteristics(
            char_keys, self.release_config, subchar_values,
        )

        assert CalculatedCharacteristic.objects.count() == 0
        assert len(instances) == len(char_keys)
        assert all(isinstance(i, CalculatedCharacteristic) for i in instances)
        assert all(i.pk is None for i in instances)
        assert set(values.keys()) == set(char_keys)

    def test_build_tsqmi_returns_unsaved_instance(self):
        char_values = {
            c.key: 0.1 for c in SupportedCharacteristic.objects.all()
        }

        tsqmi = self.services.build_tsqmi(self.release_config, char_values)

        assert TSQMI.objects.count() == 0
        assert isinstance(tsqmi, TSQMI)
        assert tsqmi.pk is None
        assert tsqmi.repository == self.repository
        assert isinstance(tsqmi.value, float)

    def test_persist_all_writes_in_one_transaction(self):
        """persist_all envolve as 5 camadas em transaction.atomic e
        retorna serializers."""
        collected = self._build_collected_metrics_for_all_measures()
        measure_keys = [m.key for m in SupportedMeasure.objects.all()]
        subchar_keys = [
            s.key for s in self.release_config.get_subcharacteristics_qs()
        ]
        char_keys = [
            c.key for c in self.release_config.get_characteristics_qs()
        ]

        measures, measure_values = self.services.build_calculated_measures(
            measure_keys, self.release_config, collected,
        )
        subchars, subchar_values = self.services.build_calculated_subcharacteristics(
            subchar_keys, self.release_config, measure_values,
        )
        chars, char_values = self.services.build_calculated_characteristics(
            char_keys, self.release_config, subchar_values,
        )
        tsqmi = self.services.build_tsqmi(self.release_config, char_values)

        response = self.services.persist_all(
            collected, measures, subchars, chars, tsqmi,
        )

        # Tudo persistido
        assert CollectedMetric.objects.count() == len(collected)
        assert CalculatedMeasure.objects.count() == len(measures)
        assert CalculatedSubCharacteristic.objects.count() == len(subchars)
        assert CalculatedCharacteristic.objects.count() == len(chars)
        assert TSQMI.objects.count() == 1

        # Resposta tem as 5 chaves serializadas
        for key in ('metrics', 'measures', 'subcharacteristics',
                    'characteristics', 'tsqmi'):
            assert key in response
