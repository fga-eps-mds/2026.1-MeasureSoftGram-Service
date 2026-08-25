from django.test import TestCase
from staticfiles import SUPPORTED_MEASURES

from measures.models import SupportedMeasure
from metrics.models import SupportedMetric
from organizations.management.commands.load_initial_data import Command


def required_metric_keys():
    """Toda métrica exigida por alguma medida suportada pelo msgram-core."""
    keys = set()
    for measure_data in SUPPORTED_MEASURES:
        measure_key = next(iter(measure_data))
        keys.update(measure_data[measure_key]["metrics"])
    return keys


class RuntimeMetricsSupportTestCase(TestCase):
    """
    O catálogo de métricas do Service precisa cobrir tudo que as medidas do
    msgram-core exigem. Quando o core ganha medidas novas e o Service não
    acompanha, create_suported_measures() aborta e derruba a carga inicial
    inteira, junto de todo teste que depende dela.
    """

    def setUp(self):
        self.command = Command()

    def test_every_metric_required_by_a_supported_measure_is_registered(self):
        self.command.create_supported_metrics()

        registered = set(SupportedMetric.objects.values_list("key", flat=True))

        self.assertEqual(
            required_metric_keys() - registered,
            set(),
            "Há medidas do msgram-core exigindo métricas que o Service não cadastra.",
        )

    def test_create_supported_measures_registers_every_measure_of_the_core(self):
        self.command.create_supported_metrics()
        self.command.create_suported_measures()

        expected = {next(iter(measure)) for measure in SUPPORTED_MEASURES}
        registered = set(SupportedMeasure.objects.values_list("key", flat=True))

        self.assertEqual(expected - registered, set())
