from collections import defaultdict
from typing import Dict, List, Tuple

from django.db import transaction

from characteristics.models import CalculatedCharacteristic, SupportedCharacteristic
from characteristics.serializers import CalculatedCharacteristicSerializer
from measures.models import CalculatedMeasure, SupportedMeasure
from measures.serializers import CalculatedMeasureSerializer
from metrics.models import CollectedMetric, SupportedMetric
from metrics.serializers import CollectedMetricSerializer
from resources import (
    calculate_characteristics,
    calculate_measures,
    calculate_subcharacteristics,
    calculate_tsqmi,
)
from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)
from subcharacteristics.serializers import CalculatedSubCharacteristicSerializer
from tsqmi.models import TSQMI
from tsqmi.serializers import TSQMISerializer


# Métricas multi-valor (lista de floats por arquivo) — espelha
# SupportedMetric.get_latest_metric_value em metrics/models.py:46.
_LISTED_FIL_METRICS = frozenset({
    'coverage',
    'complexity',
    'functions',
    'comment_lines_density',
    'duplicated_lines_density',
})
_UTS_METRICS = frozenset({'test_execution_time', 'tests'})
_GITHUB_METRICS = frozenset({
    'total_issues',
    'resolved_issues',
    'sum_ci_feedback_times',
    'total_builds',
})


class MathModelServices:
    """
    Orquestra o cálculo do modelo matemático em duas fases:

    1. build_*: constrói entidades em memória a partir do payload da
       Action, sem tocar o banco. Permite que falhas matemáticas
       aconteçam antes de qualquer escrita.
    2. persist_all: dentro de transaction.atomic, persiste as 5 camadas
       em sequência. Falha em qualquer passo dispara rollback completo.

    A leitura de CollectedMetric do banco com janela de 20min
    (metrics/models.py:113) sai do fluxo — métricas vêm exclusivamente
    do payload, conforme Cenário 3 da US12.
    """

    def __init__(self, repository, product):
        self.repository = repository
        self.product = product

    # ---------- FASE 1: build em memória ----------

    def build_collected_metrics(self, data: dict) -> List[CollectedMetric]:
        """Constrói instâncias não-persistidas de CollectedMetric a
        partir do payload bruto da Action (SonarQube + GitHub)."""
        supported_metrics = {
            sm.key: sm for sm in SupportedMetric.objects.all()
        }

        collected: List[CollectedMetric] = []

        if data.get('github'):
            for metric in data['github']['metrics']:
                key = metric['name']
                if key not in supported_metrics:
                    continue
                collected.append(
                    CollectedMetric(
                        metric=supported_metrics[key],
                        value=float(metric['value']),
                        repository=self.repository,
                        qualifier='TRK',
                    )
                )

        if data.get('sonarqube'):
            for component in data['sonarqube']['components']:
                for obj in component['measures']:
                    key = obj['metric']
                    if key not in supported_metrics:
                        continue
                    collected.append(
                        CollectedMetric(
                            qualifier=component['qualifier'],
                            path=component['path'],
                            metric=supported_metrics[key],
                            value=float(obj['value']),
                            repository=self.repository,
                        )
                    )

        return collected

    def build_calculated_measures(
        self,
        measure_keys: List[str],
        release_configuration,
        collected_metrics: List[CollectedMetric],
    ) -> Tuple[List[CalculatedMeasure], Dict[str, float]]:
        """Calcula medidas a partir das métricas em memória."""
        metric_index = self._index_metrics_by_key(collected_metrics)

        qs = SupportedMeasure.objects.filter(
            key__in=measure_keys
        ).prefetch_related('metrics')

        core_params = {'measures': []}
        for measure in qs:
            metric_params = self._resolve_metric_params_in_memory(
                measure, metric_index,
            )
            if metric_params:
                core_params['measures'].append({
                    'key': measure.key,
                    'metrics': [
                        {
                            'key': key,
                            'value': (
                                [float(v) for v in value]
                                if isinstance(value, list)
                                else [float(value)]
                            ),
                        }
                        for key, value in metric_params.items()
                    ],
                })

        calculated_result = calculate_measures(
            core_params, release_configuration.data,
        )
        calculated_values = {
            m['key']: m['value'] for m in calculated_result['measures']
        }

        instances: List[CalculatedMeasure] = []
        for measure in qs:
            if measure.key not in calculated_values:
                continue
            instances.append(
                CalculatedMeasure(
                    measure=measure,
                    value=calculated_values[measure.key],
                    repository=self.repository,
                )
            )

        return instances, calculated_values

    def build_calculated_subcharacteristics(
        self,
        subcharacteristic_keys: List[str],
        release_configuration,
        measure_values: Dict[str, float],
    ) -> Tuple[List[CalculatedSubCharacteristic], Dict[str, float]]:
        """Calcula subcaracterísticas a partir das medidas em memória."""
        qs = SupportedSubCharacteristic.objects.filter(
            key__in=subcharacteristic_keys
        ).prefetch_related('measures')

        core_params = {'subcharacteristics': []}
        for subchar in qs:
            measure_params = self._resolve_measure_params_in_memory(
                subchar, release_configuration, measure_values,
            )
            core_params['subcharacteristics'].append({
                'key': subchar.key,
                'measures': measure_params,
            })

        calculated_result = calculate_subcharacteristics(core_params)
        calculated_values = {
            s['key']: s['value']
            for s in calculated_result['subcharacteristics']
        }

        instances: List[CalculatedSubCharacteristic] = []
        for subchar in qs:
            instances.append(
                CalculatedSubCharacteristic(
                    subcharacteristic=subchar,
                    value=calculated_values[subchar.key],
                    repository=self.repository,
                )
            )

        return instances, calculated_values

    def build_calculated_characteristics(
        self,
        characteristic_keys: List[str],
        release_configuration,
        subcharacteristic_values: Dict[str, float],
    ) -> Tuple[List[CalculatedCharacteristic], Dict[str, float]]:
        """Calcula características a partir das subcaracterísticas
        em memória."""
        qs = SupportedCharacteristic.objects.filter(
            key__in=characteristic_keys
        ).prefetch_related('subcharacteristics')

        core_params = {'characteristics': []}
        for char in qs:
            subchars_params = self._resolve_subcharacteristic_params_in_memory(
                char, release_configuration, subcharacteristic_values,
            )
            core_params['characteristics'].append({
                'key': char.key,
                'subcharacteristics': subchars_params,
            })

        calculated_result = calculate_characteristics(core_params)
        calculated_values = {
            c['key']: c['value']
            for c in calculated_result['characteristics']
        }

        instances: List[CalculatedCharacteristic] = []
        for char in qs:
            instances.append(
                CalculatedCharacteristic(
                    characteristic=char,
                    value=calculated_values[char.key],
                    repository=self.repository,
                )
            )

        return instances, calculated_values

    def build_tsqmi(
        self,
        release_configuration,
        characteristic_values: Dict[str, float],
    ) -> TSQMI:
        """Calcula o TSQMI final a partir das características em memória.

        Retorna instância não persistida.
        """
        chars_params = []
        for char_data in release_configuration.data['characteristics']:
            key = char_data['key']
            weight = release_configuration.get_characteristic_weight(key)
            if weight:
                chars_params.append({
                    'key': key,
                    'value': characteristic_values.get(key),
                    'weight': weight,
                })

        core_params = {
            'tsqmi': {'key': 'tsqmi', 'characteristics': chars_params},
        }
        calculated_result = calculate_tsqmi(core_params)
        tsqmi_value = calculated_result.get('tsqmi')[0]['value']

        return TSQMI(repository=self.repository, value=tsqmi_value)

    # ---------- FASE 2: persistência atômica ----------

    @transaction.atomic
    def persist_all(
        self,
        collected_metrics: List[CollectedMetric],
        calculated_measures: List[CalculatedMeasure],
        calculated_subchars: List[CalculatedSubCharacteristic],
        calculated_chars: List[CalculatedCharacteristic],
        tsqmi: TSQMI,
    ) -> dict:
        """Persiste as 5 camadas em uma única transação atômica.

        Falha em qualquer bulk_create dispara rollback completo via
        propagação de exceção pra fora do @transaction.atomic.
        """
        saved_metrics = CollectedMetric.objects.bulk_create(collected_metrics)
        saved_measures = CalculatedMeasure.objects.bulk_create(calculated_measures)
        saved_subchars = CalculatedSubCharacteristic.objects.bulk_create(
            calculated_subchars,
        )
        saved_chars = CalculatedCharacteristic.objects.bulk_create(
            calculated_chars,
        )
        tsqmi.save()

        return {
            'metrics': CollectedMetricSerializer(saved_metrics, many=True).data,
            'measures': CalculatedMeasureSerializer(saved_measures, many=True).data,
            'subcharacteristics': CalculatedSubCharacteristicSerializer(
                saved_subchars, many=True,
            ).data,
            'characteristics': CalculatedCharacteristicSerializer(
                saved_chars, many=True,
            ).data,
            'tsqmi': TSQMISerializer(tsqmi).data,
        }

    # ---------- helpers in-memory ----------

    @staticmethod
    def _index_metrics_by_key(
        collected_metrics: List[CollectedMetric],
    ) -> Dict[str, List[CollectedMetric]]:
        """Agrupa métricas por SupportedMetric.key."""
        index: Dict[str, List[CollectedMetric]] = defaultdict(list)
        for cm in collected_metrics:
            index[cm.metric.key].append(cm)
        return index

    @staticmethod
    def _resolve_metric_params_in_memory(
        measure: SupportedMeasure,
        metric_index: Dict[str, List[CollectedMetric]],
    ) -> Dict[str, object]:
        """Substitui SupportedMeasure.get_latest_metric_params(repo)
        lendo do índice em memória.

        Replica a lógica de SupportedMetric.get_latest_metric_value
        (metrics/models.py:46) sem janela de 20min e sem ir ao banco.

        Resolve também o write/read TRK/FIL inconsistente (Service #9):
        métricas GitHub são escritas com qualifier='TRK' em
        build_collected_metrics e lidas aqui também filtrando 'TRK'
        — coerente em ambas as pontas.
        """
        # arquivos com ncloc=0 são excluídos das métricas listed FIL,
        # espelhando metrics/models.py:125-141.
        empty_paths = {
            cm.path for cm in metric_index.get('ncloc', [])
            if cm.qualifier == 'FIL' and cm.value == 0
        }

        params: Dict[str, object] = {}
        for supported_metric in measure.metrics.all():
            key = supported_metric.key
            cms = metric_index.get(key, [])

            if key in _LISTED_FIL_METRICS:
                # Lista de valores (1 por arquivo). Vazia se ausente —
                # msgram-core mantém como lista (não desempacota com len!=1)
                # e medidas como passed_tests retornam 0.0 nesse caso.
                params[key] = [
                    cm.value for cm in cms
                    if cm.qualifier == 'FIL' and cm.path not in empty_paths
                ]
            elif key in _UTS_METRICS:
                params[key] = [
                    cm.value for cm in cms if cm.qualifier == 'UTS'
                ]
            elif key in _GITHUB_METRICS:
                value = next(
                    (cm.value for cm in cms if cm.qualifier == 'TRK'),
                    None,
                )
                params[key] = value if value is not None else 0
            else:
                value = next(
                    (cm.value for cm in cms if cm.qualifier == 'TRK'),
                    None,
                )
                params[key] = value if value is not None else 0

        return params

    @staticmethod
    def _resolve_measure_params_in_memory(
        subchar: SupportedSubCharacteristic,
        release_configuration,
        measure_values: Dict[str, float],
    ) -> List[dict]:
        """Substitui SupportedSubCharacteristic.get_latest_measure_params
        (subcharacteristics/models.py:50) lendo do dict em memória."""
        params = []
        for measure in subchar.measures.all():
            weight = release_configuration.get_measure_weight(measure.key)
            if weight:
                params.append({
                    'key': measure.key,
                    'value': measure_values.get(measure.key),
                    'weight': weight,
                })
        return params

    @staticmethod
    def _resolve_subcharacteristic_params_in_memory(
        char: SupportedCharacteristic,
        release_configuration,
        subchar_values: Dict[str, float],
    ) -> List[dict]:
        """Substitui SupportedCharacteristic.get_latest_subcharacteristics_params
        (characteristics/models.py:65) lendo do dict em memória."""
        params = []
        for subchar in char.subcharacteristics.all():
            weight = release_configuration.get_subcharacteristic_weight(
                subchar.key,
            )
            if weight:
                params.append({
                    'key': subchar.key,
                    'value': subchar_values.get(subchar.key),
                    'weight': weight,
                })
        return params
