from typing import Iterable, Set, Union

from django.db import models
from django.utils import timezone

import utils
from utils.managers import CacheManager


class SupportedSubCharacteristic(models.Model):
    """
    Classe que abstrai uma subcaracterística suportada pelo sistema.
    """

    objects = CacheManager()

    name = models.CharField(max_length=128)
    key = models.CharField(max_length=128, unique=True)
    description = models.TextField(
        max_length=512,
        null=True,
        blank=True,
    )

    measures = models.ManyToManyField(
        'measures.SupportedMeasure',
        related_name='related_subcharacteristics',
        blank=True,
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save para validar se o campo `key` é valido
        """
        if not self.key:
            self.key = utils.namefy(self.name)
        super().save(*args, **kwargs)

    def get_latest_subcharacteristic_value(self) -> Union[float, None]:
        """
        Metodo que recupera o valor mais recente da subcaracterística
        """
        if latest_subchar := self.calculated_subcharacteristics.first():
            return latest_subchar.value
        return None

    def get_latest_measure_params(self, pre_config) -> dict:
        """
        Função que recupera os valores mais recentes das
        medidas que essa medida depende para ser calculada

        TODO: - Melhorar a query para o banco de dados.
              - Desconfio que aqui esteja rolando vários inner joins

        raises:
            utils.exceptions.MeasureNotDefinedInReleaseConfigurationuration:
                Caso a uma medida não esteja definida no pre_config
        """
        measures_params = []

        for measure in self.measures.all():
            weight = pre_config.get_measure_weight(measure.key)
            if weight:
                measures_params.append(
                    {
                        'key': measure.key,
                        'value': measure.get_latest_measure_value(),
                        'weight': weight,
                    }
                )

        return measures_params

    def has_unsupported_measures(
        self,
        measures_keys: Iterable[str],
    ) -> Set[str]:
        """
        Verifica se todas as medidas passadas no argumento `measures_keys`
        estão associadas a subcaracterística no modelo.

        Retorna um set com as medidas que não estão associadas
        a subcaracterística.
        """
        measures_keys = set(measures_keys)

        qs = self.measures.all()
        related_measures: Set[str] = set(qs.values_list('key', flat=True))

        return measures_keys - related_measures

    @staticmethod
    def has_unsupported_subcharacteristics(
        selected_subcharacteristics_keys: Iterable[str],
    ) -> Set[str]:
        """
        Verifica se existe alguma subcaracterística não suportada, e caso
        exista é retornado a lista das keys das subcaracterísticas
        não suportadas.
        """
        return utils.has_unsupported_entity(
            selected_subcharacteristics_keys,
            SupportedSubCharacteristic,
        )


class CalculatedSubCharacteristic(models.Model):
    """
    Tabela que aramazena os valores calculados das subcaracterísticas.
    """

    class Meta:
        ordering = ['-created_at']

    subcharacteristic = models.ForeignKey(
        SupportedSubCharacteristic,
        related_name='calculated_subcharacteristics',
        on_delete=models.CASCADE,
    )
    value = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    repository = models.ForeignKey(
        to='organizations.Repository',
        related_name='calculated_subcharacteristics',
        on_delete=models.CASCADE,
    )
