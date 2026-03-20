from typing import Iterable, Set, Union

from django.db import models
from django.utils import timezone

import utils
from utils.managers import CacheManager


class SupportedMeasure(models.Model):
    """
    Tabela que lista as medidas suportadas.

    Essa tabela gera uma tabela NxM com a tabela SupportedMetrics. Por meio
    dessa tabela NxM que temos a associação de quais métricas são usadas para
    calcular uma medida
    """

    objects = CacheManager()

    key = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(
        max_length=512,
        null=True,
        blank=True,
    )

    # Métricas que estão associadas no cálculo dessa medida
    metrics = models.ManyToManyField(
        'metrics.SupportedMetric',
        related_name='related_measures',
        blank=True,
    )

    def __str__(self):
        return self.name

    def get_latest_metric_params(self, repository):
        """
        Função que recupera os valores mais recentes das
        métricas que essa medida depende para ser calculada

        TODO: - Melhorar a query para o banco de dados.
              - Desconfio que aqui esteja rolando vários inner joins

        """
        metric_params = {}

        for supported_metric in self.metrics.all():
            key = supported_metric.key
            value = supported_metric.get_latest_metric_value(repository)

            if value is None:
                value = 0

            metric_params[key] = value

        return metric_params

    @staticmethod
    def has_unsupported_measures(
        selected_measures_keys: Iterable[str],
    ) -> Set[str]:
        """
        Verifica se existe alguma medida não suportada, e caso exista é
        retornado a lista das keys das medidas não suportadas.

        Args:
            selected_measures_keys: Lista de keys das medidas selecionadas
        """
        return utils.has_unsupported_entity(
            selected_measures_keys,
            SupportedMeasure,
        )

    def get_latest_measure_value(self) -> Union[None, float]:
        """
        Função que recupera o valor mais recente da medida caso exista,
        caso não exista retorna None
        """
        if latest_measure := self.calculated_measures.first():
            return latest_measure.value
        return None


class CalculatedMeasure(models.Model):
    """
    Tabela que armazena todas os valores das medidas já calculadas
    """

    class Meta:
        # Aqui estamos ordenando na ordem decrescente, ou seja, nos querysets
        # os registros mais recentes vem primeiro (qs.first() == mais recente)
        ordering = ['-created_at']

    measure = models.ForeignKey(
        SupportedMeasure,
        related_name='calculated_measures',
        on_delete=models.CASCADE,
    )
    value = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    repository = models.ForeignKey(
        to='organizations.Repository',
        related_name='calculated_measures',
        on_delete=models.CASCADE,
    )
