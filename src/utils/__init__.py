import datetime as dt
import random
import string
from itertools import zip_longest
from typing import Callable, Iterable, Set

from django.db import models
from django.utils import timezone

from utils import exceptions


def chunkify(iterable, size, fillvalue=None) -> list:
    args = [iter(iterable)] * size
    return list(zip_longest(*args, fillvalue=fillvalue))


def get_random_datetime(start_date, end_date):
    return timezone.make_aware(
        dt.datetime.fromtimestamp(
            random.randint(
                int(start_date.timestamp()),
                int(end_date.timestamp()),
            )
        )
    )


def namefy(str_value):
    """Key to name"""
    return str_value.replace('_', ' ').title()


def keyfy(str_value):
    """Name to key"""
    return str_value.replace(' ', '_').lower()


def get_random_string():
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(100))


def get_random_path():
    base_dirs = [
        'src',
        'test',
        'utils',
        'apps',
        'config',
        'templates',
        'static',
        'media',
    ]

    middle_dirs = [
        'controllers',
        'models',
        'serializers',
        'views',
        'forms',
        'templatetags',
        'commands',
        'management',
    ]

    file_names = [
        'app.py',
        'config.py',
        'views.py',
        'serializers.py',
        'models.py',
        'controllers.py',
        'forms.py',
        'templatetags.py' 'pre_config.py',
        'urls.py',
        'models.py',
        'admin.py',
    ]

    base_dir = random.choice(base_dirs)
    middle_dir = random.choice(middle_dirs)
    file_name = random.choice(file_names)
    return f'{base_dir}/{middle_dir}/{file_name}'


def get_random_qualifier():
    return random.choice(['UTS', 'FIL', 'DIR'])


# pylint: disable=too-many-return-statements
def get_random_value(metric_type):  # noqa: max-complexity: 13
    if metric_type == 'INT':
        return random.randint(0, 100)

    if metric_type == 'FLOAT':
        # Para valores aleatórios entre 0 e 100
        # return random.random() * random.randint(0, 100)

        # Para valores variando perto de 50
        return random.uniform(0, 100)

    if metric_type == 'PERCENT':
        return random.random()

    if metric_type == 'BOOL':
        return random.choice([True, False])

    if metric_type == 'STRING':
        # Por mais que o tipo seja uma string, o valor da única
        # métrica que tem esse tipo no sonarqube é a métrica
        # `new_development_cost` cujo valor é um float
        return random.uniform(0, 1000)

    if metric_type == 'DATA':
        return random.randint(0, 100)

    if metric_type == 'WORK_DUR':
        return random.randint(0, 100)

    if metric_type == 'DISTRIB':
        return random.randint(0, 100)

    if metric_type == 'RATING':
        return random.randint(0, 100)

    if metric_type == 'LEVEL':
        return random.choice([True, False])

    if metric_type == 'MILLISEC':
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=90)
        datetime = get_random_datetime(start_date, end_date)
        return datetime.timestamp()

    raise exceptions.RandomMetricTypeException(
        f'Metric type not supported: {metric_type}'
    )


def has_unsupported_entity(
    selected_entities_keys: Iterable[str],
    model: models.Model,
) -> Set[str]:
    """
    Função que verifica e retorna as entidades que não são suportadas

    Args:
        selected_entities_keys: Lista de chaves das entidades selecionadas
        model: Modelo do qual será verificado se as entidades selecionadas
    """

    selected_entities_set = set(selected_entities_keys)
    qs = model.objects.filter(key__in=selected_entities_set)
    supported_entities_set = {entity.key for entity in qs}
    return selected_entities_set - supported_entities_set


@staticmethod
def validate_entity(
    selected_entity_set: Iterable[str],
    fun: Callable[[Iterable[str]], Iterable[str]],
) -> str:
    """ """
    unsuported: set = fun(selected_entity_set)
    unsuported: list = [f'`{key}`' for key in unsuported]
    unsuported: str = ', '.join(unsuported)
    return unsuported


class DateRange:
    def __init__(self, start: dt.datetime, end: dt.datetime):
        if not isinstance(start, dt.datetime):
            raise TypeError('start must be a datetime.date')

        if not isinstance(end, dt.datetime):
            raise TypeError('end must be a datetime.date')

        self.start = start
        self.end = end

    @staticmethod
    def create_from_today(days: int):
        return DateRange(
            start=dt.datetime.today() - dt.timedelta(days=days),
            end=dt.datetime.today(),
        )

    def __str__(self):
        return f'{self.start} - {self.end}'

    def __repr__(self):
        return f'{self.start} - {self.end}'
