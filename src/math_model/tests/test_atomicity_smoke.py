"""
Smoke tests do endpoint de cálculo do modelo matemático.

Cobertura dos cenários da US12:
- Cenário 1 (fluxo feliz): payload válido → 201 + persistência completa.
- Cenário 2 (falha mid-cálculo): mock força exceção → rollback total.

Cenário 2 prova a "DOR DOCUMENTADA: ausência de transação" registrada
em src/math_model/CLAUDE.md. Sem @transaction.atomic, falha em qualquer
passo deixa rastros dos passos anteriores. Após o fix, vira green.
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

    def test_fluxo_feliz_persiste_todas_as_camadas(self):
        """
        Cenário 1 da US: payload válido executa os 5 passos sem mock,
        retorna 201 e persiste todas as camadas.

        Serve de rede de proteção pro refactor "calcula em memória →
        persiste no fim": shape da resposta e contagens não-zero
        devem ser preservadas, mesmo que a implementação interna mude
        (banco vs payload, intercalado vs no fim).

        Não compara valores — só shape — pra ficar robusto a mudanças
        de leitura (banco com janela 20min vs payload em memória) que
        podem alterar entradas do msgram-core.
        """
        empty_payload = {
            'github': {'metrics': []},
            'sonarqube': {'components': []},
        }

        response = self.client.post(self.url, empty_payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED, (
            f'esperava 201, recebeu {response.status_code}: '
            f'{response.content!r}'
        )

        # Resposta tem as 5 chaves esperadas
        body = response.json()
        for key in ('metrics', 'measures', 'subcharacteristics',
                    'characteristics', 'tsqmi'):
            assert key in body, f'chave "{key}" ausente na resposta'

        # As 4 camadas calculadas devem ter sido persistidas
        assert CalculatedMeasure.objects.count() > 0, 'medidas não persistiram'
        assert CalculatedSubCharacteristic.objects.count() > 0, (
            'subcharacteristics não persistiram'
        )
        assert CalculatedCharacteristic.objects.count() > 0, (
            'characteristics não persistiram'
        )
        assert TSQMI.objects.count() == 1, 'TSQMI não persistiu (esperava 1)'
