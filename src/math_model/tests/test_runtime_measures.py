"""
Testes do recorte das runtime measures no cálculo do modelo matemático.

O msgram-core 1.5.x trouxe medidas de runtime (response_time,
cpu_utilization, memory_utilization) que são validadas por um schema de
comparação entre duas releases, alimentado por dados de APM. O Service
cadastra essas medidas (o core exige que o catálogo esteja completo), mas
não tem coletor de APM ainda, então elas não podem entrar no
calculate_measures padrão. Ver issue #56.

Os testes abaixo chamam o msgram-core de verdade: se o filtro sumir, o
core levanta ValidationError e eles quebram.
"""

from unittest import mock

from resources import calculate_measures

from math_model import utils
from math_model.services import MathModelServices
from math_model.utils import RUNTIME_MEASURE_KEYS
from measures.models import SupportedMeasure
from metrics.models import CollectedMetric, SupportedMetric
from release_configuration.models import ReleaseConfiguration
from utils import staticfiles
from utils.tests import APITestCaseExpanded


class RuntimeMeasuresAreSkippedTest(APITestCaseExpanded):
    def setUp(self):
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        ReleaseConfiguration.objects.get_or_create(
            name="Default pre-config",
            data=staticfiles.DEFAULT_PRE_CONFIG,
            product=self.product,
        )
        self.release_config = self.product.release_configuration.first()
        self.services = MathModelServices(self.repository, self.product)

    def _collected_metrics(self):
        """CollectedMetric não persistidos cobrindo as métricas das medidas
        comuns (as de runtime não têm coletor, por definição)."""
        metrics = []
        groups = [
            (
                [
                    "coverage",
                    "complexity",
                    "functions",
                    "comment_lines_density",
                    "duplicated_lines_density",
                ],
                "FIL",
            ),
            (["test_execution_time", "tests"], "UTS"),
            (["test_failures", "test_errors"], "TRK"),
            (
                [
                    "total_issues",
                    "resolved_issues",
                    "sum_ci_feedback_times",
                    "total_builds",
                ],
                "TRK",
            ),
        ]

        for keys, qualifier in groups:
            for supported_metric in SupportedMetric.objects.filter(key__in=keys):
                for value in (0.1, 0.2):
                    metrics.append(
                        CollectedMetric(
                            value=value,
                            metric=supported_metric,
                            repository=self.repository,
                            qualifier=qualifier,
                        )
                    )

        return metrics

    def test_runtime_measures_are_registered_in_the_database(self):
        """Guarda contra teste vazio: se as runtime measures não estivessem
        cadastradas, o filtro não teria o que filtrar."""
        registered = set(
            SupportedMeasure.objects.filter(
                key__in=RUNTIME_MEASURE_KEYS,
            ).values_list("key", flat=True)
        )

        assert RUNTIME_MEASURE_KEYS
        assert registered == set(RUNTIME_MEASURE_KEYS)

    def test_runtime_measures_are_not_sent_to_the_core(self):
        """Mesmo pedindo TODAS as medidas cadastradas, o payload que chega
        ao msgram-core não contém nenhuma runtime measure."""
        measure_keys = [m.key for m in SupportedMeasure.objects.all()]
        expected_keys = set(measure_keys) - set(RUNTIME_MEASURE_KEYS)

        assert set(measure_keys) & set(RUNTIME_MEASURE_KEYS)

        # wraps: o core roda de verdade (e ele que rejeitaria uma runtime
        # measure); o mock existe so pra inspecionar o payload enviado.
        with mock.patch(
            "math_model.services.calculate_measures",
            wraps=calculate_measures,
        ) as spy:
            instances, values = self.services.build_calculated_measures(
                measure_keys,
                self.release_config,
                self._collected_metrics(),
            )

        spy.assert_called_once()
        core_params = spy.call_args.args[0]
        sent_keys = {measure["key"] for measure in core_params["measures"]}

        assert sent_keys.isdisjoint(RUNTIME_MEASURE_KEYS)
        assert sent_keys == expected_keys
        assert set(values.keys()) == expected_keys
        assert {i.measure.key for i in instances} == expected_keys


class DeriveRuntimeMeasureKeysTest(APITestCaseExpanded):
    """A lista de runtime measures é derivada do catálogo do msgram-core,
    não escrita à mão: medida nova que dependa de métrica de observabilidade
    entra sozinha."""

    def test_matches_the_runtime_measures_of_the_current_core(self):
        """Tripwire proposital: crava as chaves do core 1.5.x.

        A derivacao acompanha o core sozinha, mas se uma metrica for renomeada
        la a intersecao vira vazia e o filtro degenera em no-op silencioso.
        Este teste quebra nesse caso. Falhou depois de subir o core? Confira se
        RUNTIME_AVAILABLE_METRICS ainda casa com o catalogo dele antes de so
        atualizar a lista abaixo.
        """
        assert set(RUNTIME_MEASURE_KEYS) == {
            "response_time",
            "cpu_utilization",
            "memory_utilization",
        }

    def test_picks_up_a_new_measure_that_depends_on_a_runtime_metric(self):
        fake_catalogue = [
            {"test_coverage": {"metrics": ["coverage"]}},
            {"future_runtime_measure": {"metrics": ["endpoint_calls", "cpu_usage"]}},
        ]

        with mock.patch.object(utils, "SUPPORTED_MEASURES", fake_catalogue):
            derived = utils._derive_runtime_measure_keys()

        assert derived == frozenset({"future_runtime_measure"})
