from typing import Iterable, Set, Union

from django.db import models
from django.utils import timezone

import utils
from utils.managers import CacheManager


class SupportedCharacteristic(models.Model):
    """
    Classe que abstrai uma característica suportada pelo sistema.
    """

    objects = CacheManager()

    name = models.CharField(max_length=128)
    key = models.CharField(max_length=128, unique=True)
    description = models.TextField(
        max_length=512,
        null=True,
        blank=True,
    )
    subcharacteristics = models.ManyToManyField(
        'subcharacteristics.SupportedSubCharacteristic',
        related_name='related_characteristics',
        blank=True,
    )

    def get_latest_characteristic_value(self) -> Union[float, None]:
        """
        Metodo que recupera o valor mais recente da característica
        """
        if latest_char := self.calculated_characteristics.first():
            return latest_char.value
        return None

    def get_latest_characteristics_params(self, pre_config: dict) -> dict:
        """
        Função que recupera os valores mais recentes das características
        que o tsqmi depende para ser calculada

        TODO: - Melhorar a query para o banco de dados.
              - Desconfio que aqui esteja rolando vários inner joins

        """
        chars_params = []

        for characteristic in self.__class__.objects.all():
            key = characteristic.key
            weight = pre_config.get_characteristic_weight(key)
            if weight:
                value = characteristic.get_latest_characteristic_value()

                chars_params.append(
                    {
                        'key': key,
                        'value': value,
                        'weight': weight,
                    }
                )

        return chars_params

    def get_latest_subcharacteristics_params(self, pre_config: dict) -> dict:
        """
        Função que recupera os valores mais recentes das subcaracterísticas
        que essa características depende para ser calculada
        """

        subchars_params = []

        for subcharacteristic in self.subcharacteristics.all():
            key = subcharacteristic.key
            weight = pre_config.get_subcharacteristic_weight(key)
            if weight:
                value = subcharacteristic.get_latest_subcharacteristic_value()

                subchars_params.append(
                    {
                        'key': key,
                        'value': value,
                        'weight': weight,
                    }
                )

        return subchars_params

    def has_unsupported_subcharacteristics(
        self,
        subcharacteristics_keys: Iterable[str],
    ) -> Set[str]:
        """
        Verifica se todas as subcaracterísticas passadas no argumento
        `subcharacteristics_keys` estão associadas a característica no modelo.

        Retorna um set com as subcaracterísticas que não estão associadas
        a característica.
        """
        subcharacteristics_keys = set(subcharacteristics_keys)

        qs = self.subcharacteristics.all()
        related_subcharacteristics: Set[str] = set(
            qs.values_list('key', flat=True)
        )

        return subcharacteristics_keys - related_subcharacteristics

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save para validar se o campo `key` é valido
        """
        if not self.key and self.name:
            self.key = utils.namefy(self.name)

        elif not self.name and self.key:
            self.name = utils.keyfy(self.key)

        super().save(*args, **kwargs)

    @staticmethod
    def has_unsupported_characteristics(
        selected_characteristics_keys: Iterable[str],
    ) -> Set[str]:
        """
        Verifica se existe alguma característica não suportada, e caso exista
        é retornado a lista das keys das características não suportadas.
        """
        return utils.has_unsupported_entity(
            selected_characteristics_keys,
            SupportedCharacteristic,
        )


class BalanceMatrix(models.Model):
    TYPE_CHOICES = (
        ('+', 'Positive'),  # Diretamente proporcional
        ('-', 'Negative'),  # Inversamente proporcional
    )

    source_characteristic = models.ForeignKey(
        SupportedCharacteristic,
        on_delete=models.CASCADE,
        related_name='source_characteristic',
    )
    target_characteristic = models.ForeignKey(
        SupportedCharacteristic,
        on_delete=models.CASCADE,
        related_name='target_characteristic',
    )
    relation_type = models.CharField(max_length=1, choices=TYPE_CHOICES)

    class Meta:
        unique_together = ['source_characteristic', 'target_characteristic']

    def __str__(self):
        return f'{self.source_characteristic} {self.relation_type} {self.target_characteristic}'


class CalculatedCharacteristic(models.Model):
    """
    Tabela que armazena os valores calculados das características.
    """

    class Meta:
        # Aqui estamos ordenando na ordem decrescente, ou seja, nos querysets
        # os registros mais recentes vem primeiro (qs.first() == mais recente)
        ordering = ['-created_at']
        unique_together = ['repository', 'release', 'characteristic']

    characteristic = models.ForeignKey(
        SupportedCharacteristic,
        related_name='calculated_characteristics',
        on_delete=models.CASCADE,
    )
    value = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    repository = models.ForeignKey(
        to='organizations.Repository',
        related_name='calculated_characteristics',
        on_delete=models.CASCADE,
    )
    release = models.ForeignKey(
        to='releases.Release',
        related_name='calculated_characteristics',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
