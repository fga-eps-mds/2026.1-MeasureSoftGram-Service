from typing import Dict, Iterable

from django.db import models
from django.utils import timezone


class Goal(models.Model):
    """
    Tabela que armazena os objetivos de qualidade
    de um projeto na perspectiva de qualidade
    """

    class Meta:
        ordering = ('-created_at',)

    created_at = models.DateTimeField(default=timezone.now)
    data = models.JSONField()
    created_by = models.ForeignKey(
        to='accounts.CustomUser',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        to='organizations.Product',
        related_name='goals',
        on_delete=models.CASCADE,
    )

    @staticmethod
    def validate_goal(goal_dict: Dict[str, int]):
        return True

    def save(self, *args, **kwargs):
        if self.id:
            raise ValueError("It's not allowed to update a goal")

        self.validate_goal(self.data)
        return super().save(*args, **kwargs)


class Equalizer:
    """
    Classe que implementa a lógica de modificação dos pesos no equalizador
    """

    # TODO: Só as das pré-configuração
    BALANCE_MATRIX = {
        'functional_suitability': {
            '+': {
                'usability',
                'reliability',
                'maintainability',
            },
            '-': {
                'performance_efficiency',
                'security',
            },
        },
        'performance_efficiency': {
            '+': set(),
            '-': {
                'functional_suitability',
                'usability',
                'compatibility',
                'security',
                'maintainability',
                'portability',
            },
        },
        'usability': {
            '+': {
                'functional_suitability',
                'reliability',
            },
            '-': {
                'performance_efficiency',
            },
        },
        'compatibility': {
            '+': {'portability'},
            '-': {'security'},
        },
        'reliability': {
            '+': {'functional_suitability', 'usability', 'maintainability'},
            '-': set(),
        },
        'security': {
            '+': {'reliability'},
            '-': {'performance_efficiency', 'usability', 'compatibility'},
        },
        'maintainability': {
            '+': {
                'functional_suitability',
                'compatibility',
                'reliability',
                'portability',
            },
            '-': {
                'performance_efficiency',
            },
        },
        'portability': {
            '+': {
                'compatibility',
                'maintainability',
            },
            '-': {
                'performance_efficiency',
            },
        },
    }

    def __init__(self, entities_keys: Iterable[str]):
        self.default_setup = {entity_key: 50 for entity_key in entities_keys}

        # self.default_setup = {
        #     'functional_suitability': 50,
        #     'performance_efficiency': 50,
        #     'security': 50,

        #     # 'usability': 50,
        #     # 'compatibility': 50,
        #     # 'reliability': 50,
        #     # 'maintainability': 50,
        #     # 'portability': 50,
        # }

    @staticmethod
    def force_min_max(value):
        return max(0, min(100, value))

    def update(self, entity_key: str, delta: int, allow_dynamic: bool = False):
        self.default_setup[entity_key] += delta

        self.default_setup[entity_key] = self.force_min_max(
            self.default_setup[entity_key],
        )

        if allow_dynamic:
            return

        for related_entity in self.BALANCE_MATRIX[entity_key]['+']:
            if related_entity in self.default_setup:
                self.default_setup[related_entity] += delta

                self.default_setup[related_entity] = self.force_min_max(
                    self.default_setup[related_entity],
                )

        for related_entity in self.BALANCE_MATRIX[entity_key]['-']:
            if related_entity in self.default_setup:
                self.default_setup[related_entity] += -1 * delta

                self.default_setup[related_entity] = self.force_min_max(
                    self.default_setup[related_entity],
                )

    def get_goal(self):
        return self.default_setup
