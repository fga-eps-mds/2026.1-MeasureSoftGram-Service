"""
Smoke tests do endpoint de cálculo do modelo matemático.

Cobertura dos cenários da US12:
- Cenário 1 (fluxo feliz): payload válido → 201 + persistência completa.
- Cenário 2 (falha mid-cálculo): mock força exceção → rollback total.
- Cenário 3 (sem janela 20min): cálculo não lê CollectedMetric do banco
  durante o POST — usa o payload em memória.

Cenário 2 prova a "DOR DOCUMENTADA: ausência de transação" registrada
em src/math_model/CLAUDE.md. Sem @transaction.atomic, falha em qualquer
passo deixa rastros dos passos anteriores.

Cenário 3 prova que o cálculo deixou de depender da janela de 20min em
metrics/models.py:113. Após o refactor "calcula em memória", a função
SupportedMetric.get_latest_metric_value não é consultada durante o POST.
"""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
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


def _full_payload():
    """Payload realista que cobre todas as 14 métricas alimentando as
    8 medidas do DEFAULT_PRE_CONFIG.

    Espelha o que a Action manda em produção (SonarQube components +
    GitHub metrics)."""
    return {
        'github': {
            'metrics': [
                {'name': 'total_issues', 'value': 10},
                {'name': 'resolved_issues', 'value': 8},
                {'name': 'sum_ci_feedback_times', 'value': 300},
                {'name': 'total_builds', 'value': 5},
            ],
        },
        'sonarqube': {
            'components': [
                {
                    'qualifier': 'FIL',
                    'path': 'src/foo.py',
                    'measures': [
                        {'metric': 'coverage', 'value': 80.0},
                        {'metric': 'complexity', 'value': 5},
                        {'metric': 'functions', 'value': 10},
                        {'metric': 'comment_lines_density', 'value': 20.0},
                        {'metric': 'duplicated_lines_density', 'value': 0.0},
                        {'metric': 'ncloc', 'value': 100},
                    ],
                },
                {
                    'qualifier': 'FIL',
                    'path': 'src/bar.py',
                    'measures': [
                        {'metric': 'coverage', 'value': 60.0},
                        {'metric': 'complexity', 'value': 8},
                        {'metric': 'functions', 'value': 15},
                        {'metric': 'comment_lines_density', 'value': 15.0},
                        {'metric': 'duplicated_lines_density', 'value': 5.0},
                        {'metric': 'ncloc', 'value': 200},
                    ],
                },
                {
                    'qualifier': 'UTS',
                    'path': 'tests/foo_test.py',
                    'measures': [
                        {'metric': 'tests', 'value': 5},
                        {'metric': 'test_execution_time', 'value': 100},
                    ],
                },
                # Segundo arquivo UTS necessário pra que tests/test_execution_time
                # cheguem ao msgram-core como lista (>1 valor). O helper
                # convert_metrics_to_dict em resources/analysis.py desempacota
                # listas de 1 elemento para float, o que quebra medidas que
                # exigem lista (ex: passed_tests).
                {
                    'qualifier': 'UTS',
                    'path': 'tests/bar_test.py',
                    'measures': [
                        {'metric': 'tests', 'value': 3},
                        {'metric': 'test_execution_time', 'value': 80},
                    ],
                },
                {
                    'qualifier': 'TRK',
                    'path': '',
                    'measures': [
                        {'metric': 'test_failures', 'value': 0},
                        {'metric': 'test_errors', 'value': 0},
                    ],
                },
            ],
        },
    }


@freeze_time("2024-09-08 20:00:00")
class MathModelAtomicitySmokeTest(APITestCaseExpanded):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test-user', password='test-pass'
        )
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )

        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        ReleaseConfiguration.objects.get_or_create(
            name='Default pre-config',
            data=staticfiles.DEFAULT_PRE_CONFIG,
            product=self.product,
        )
        self.release_config = self.product.release_configuration.first()

        # Pré-popula uma métrica sentinela para distinguir, no cenário 3,
        # o que veio do banco (não deveria ser usado) do que veio do
        # payload (única fonte permitida pós-refactor).
        ncloc = SupportedMetric.objects.get(key='ncloc')
        CollectedMetric.objects.create(
            value=999, metric=ncloc, repository=self.repository,
            qualifier='FIL', path='legacy/old.py',
        )
        self.initial_collected = CollectedMetric.objects.count()

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
        Cenário 2 da US12: mock força raise no passo 3
        (calculate_subcharacteristics do msgram-core).

        Estado esperado pós-falha:
            - status 400
            - CollectedMetric: == initial (nada do payload persistiu)
            - CalculatedMeasure, SubCharacteristic, Characteristic, TSQMI: 0

        Sem rollback (estado pré-fix em math_model/views.py), o passo 2
        commita CalculatedMeasures antes do passo 3 falhar — assert
        de CalculatedMeasure.count() == 0 quebra (RED).
        """
        response = self.client.post(self.url, _full_payload(), format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f'esperava 400 (CalculateModelException), recebeu '
            f'{response.status_code}: {response.content!r}'
        )

        assert CollectedMetric.objects.count() == self.initial_collected, (
            f'CollectedMetric vazou: inicial={self.initial_collected}, '
            f'atual={CollectedMetric.objects.count()}'
        )

        leaked_measures = CalculatedMeasure.objects.count()
        assert leaked_measures == 0, (
            f'BUG DE ATOMICIDADE: passo 2 vazou {leaked_measures} '
            f'CalculatedMeasure(s) apesar do passo 3 ter falhado.'
        )

        assert CalculatedSubCharacteristic.objects.count() == 0
        assert CalculatedCharacteristic.objects.count() == 0
        assert TSQMI.objects.count() == 0

    def test_fluxo_post_nao_le_collected_metric_do_banco(self):
        """
        Cenário 3 da US12 — eliminar janela de 20min.

        Spy em SupportedMetric.get_latest_metric_value (que ativa a
        janela em metrics/models.py:113). Após o refactor "calcula
        em memória", essa função não é consultada durante o POST —
        métricas vêm exclusivamente do payload da Action.
        """
        call_log = []
        original = SupportedMetric.get_latest_metric_value

        def spy(self_metric, repository):
            call_log.append(self_metric.key)
            return original(self_metric, repository)

        with patch.object(
            SupportedMetric, 'get_latest_metric_value', new=spy,
        ):
            response = self.client.post(
                self.url, _full_payload(), format='json',
            )

        assert response.status_code == status.HTTP_201_CREATED, (
            f'esperava 201, recebeu {response.status_code}: '
            f'{response.content!r}'
        )

        assert call_log == [], (
            f'BUG: fluxo do POST consultou CollectedMetric do banco '
            f'{len(call_log)} vez(es) via get_latest_metric_value: '
            f'{call_log}. Cenário 3 da US12 exige cálculo em memória '
            f'a partir do payload da Action — janela de 20min em '
            f'metrics/models.py:113 deve sair desse fluxo.'
        )

    def test_fluxo_feliz_persiste_todas_as_camadas(self):
        """
        Cenário 1 da US12: payload válido executa os 5 passos sem mock,
        retorna 201 e persiste todas as camadas em uma transação.

        Não compara valores — só shape — pra ficar robusto a mudanças
        de implementação interna.
        """
        response = self.client.post(self.url, _full_payload(), format='json')

        assert response.status_code == status.HTTP_201_CREATED, (
            f'esperava 201, recebeu {response.status_code}: '
            f'{response.content!r}'
        )

        body = response.json()
        for key in ('metrics', 'measures', 'subcharacteristics',
                    'characteristics', 'tsqmi'):
            assert key in body, f'chave "{key}" ausente na resposta'

        # Métricas do payload devem estar persistidas (além das pré-existentes).
        assert CollectedMetric.objects.count() > self.initial_collected, (
            'métricas do payload não foram persistidas'
        )

        assert CalculatedMeasure.objects.count() > 0, 'medidas não persistiram'
        assert CalculatedSubCharacteristic.objects.count() > 0, (
            'subcharacteristics não persistiram'
        )
        assert CalculatedCharacteristic.objects.count() > 0, (
            'characteristics não persistiram'
        )
        assert TSQMI.objects.count() == 1, 'TSQMI não persistiu (esperava 1)'
