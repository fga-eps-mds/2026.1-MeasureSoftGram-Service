"""
Smoke test do bug de atomicidade no endpoint de cálculo do modelo
matemático.

Cobre o Cenário 2 da US12 (Service refactor):
> Quando ocorre um erro em qualquer etapa do cálculo das hierarquias
> ou medidas, o sistema deve interromper a operação e nenhuma métrica
> parcial deve ser inserida no banco.

Hoje (sem @transaction.atomic em math_model/views.py:32-42), os
bulk_create dos passos 1 e 2 já foram commitados quando o passo 3
falha — banco fica em estado parcialmente calculado.

Este teste mocka calculate_subcharacteristics (msgram-core) com
side_effect=CalculateModelException no passo 3 e asserta que
CalculatedMeasure deveria estar vazia. Vai FALHAR no código atual
(red), provando o bug. Após o fix (transaction.atomic envolvendo
o fluxo na view), vira green.
"""
from unittest.mock import patch

from freezegun import freeze_time
from rest_framework import status

from utils.tests import APITestCaseExpanded
from utils import staticfiles
from utils.exceptions import CalculateModelException
from release_configuration.models import ReleaseConfiguration
from metrics.models import SupportedMetric, CollectedMetric
from measures.models import CalculatedMeasure
from subcharacteristics.models import CalculatedSubCharacteristic
from characteristics.models import CalculatedCharacteristic
from tsqmi.models import TSQMI


@freeze_time("2024-09-08 20:00:00")
class MathModelAtomicitySmokeTest(APITestCaseExpanded):
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

        # Pré-popula CollectedMetric pra que calculate_measures (passo 2)
        # tenha dados pra ler. Mesmo conjunto usado em test_services.py.
        listed_values = [
            'coverage', 'complexity', 'functions',
            'comment_lines_density', 'duplicated_lines_density',
        ]
        uts_values = ['test_execution_time', 'tests']
        trk_values = ['test_failures', 'test_errors']
        for values, qualifier in zip(
            [listed_values, uts_values, trk_values],
            ['FIL', 'UTS', 'TRK'],
        ):
            for metric in SupportedMetric.objects.filter(key__in=values):
                CollectedMetric.objects.create(
                    value=0.1, metric=metric, repository=self.repository,
                    qualifier=qualifier,
                )
                CollectedMetric.objects.create(
                    value=0.2, metric=metric, repository=self.repository,
                    qualifier=qualifier,
                )

        github_values = [
            'total_issues', 'resolved_issues',
            'sum_ci_feedback_times', 'total_builds',
        ]
        for metric in SupportedMetric.objects.filter(key__in=github_values):
            CollectedMetric.objects.create(
                value=1, metric=metric, repository=self.repository,
                qualifier='FIL',
            )

        self.initial_collected = CollectedMetric.objects.count()
        assert self.initial_collected > 0, 'pré-condição quebrou'

        self.url = (
            f'/api/v1/organizations/{self.org.id}'
            f'/products/{self.product.id}'
            f'/repositories/{self.repository.id}'
            f'/calculate/math-model/'
        )

    @patch(
        'math_model.services.calculate_subcharacteristics',
        side_effect=CalculateModelException(
            'simulated mid-calculation failure (passo 3)'
        ),
    )
    def test_falha_no_passo_3_deve_reverter_passos_anteriores(self, _mock):
        """
        Endpoint dispara fluxo de 5 passos. Mock força raise no passo 3
        (calculate_subcharacteristics do msgram-core).

        Estado esperado pós-falha (Cenário 2 da US):
            - status 400
            - CalculatedMeasure: 0 (passo 2 deveria ter sido revertido)
            - CalculatedSubCharacteristic, Characteristic, TSQMI: 0
            - CollectedMetric: == initial (não houve insert novo, payload vazio)

        Hoje (sem @transaction.atomic na view): passo 2 commitou N
        CalculatedMeasures antes do passo 3 raise — assert quebra (RED).
        """
        empty_payload = {
            'github': {'metrics': []},
            'sonarqube': {'components': []},
        }

        response = self.client.post(self.url, empty_payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f'esperava 400 (CalculateModelException), recebeu '
            f'{response.status_code}: {response.content!r}'
        )

        assert CollectedMetric.objects.count() == self.initial_collected, (
            f'CollectedMetric não deveria ter mudado; '
            f'inicial={self.initial_collected}, '
            f'atual={CollectedMetric.objects.count()}'
        )

        # AQUI MORA O BUG ATIVO: passo 2 (calculate_measures) commitou
        # CalculatedMeasures antes do passo 3 (subcharacteristics) bater
        # no mock e raise. Sem @transaction.atomic, esses inserts persistem.
        leaked_measures = CalculatedMeasure.objects.count()
        assert leaked_measures == 0, (
            f'BUG DE ATOMICIDADE: passo 2 vazou {leaked_measures} '
            f'CalculatedMeasure(s) apesar do passo 3 ter falhado. '
            f'Falta @transaction.atomic envolvendo o fluxo em '
            f'math_model/views.py:32-42.'
        )

        # Passos 3, 4, 5 nunca executaram — esses asserts são triviais
        # (defensivos contra regressão de fluxo).
        assert CalculatedSubCharacteristic.objects.count() == 0
        assert CalculatedCharacteristic.objects.count() == 0
        assert TSQMI.objects.count() == 0
