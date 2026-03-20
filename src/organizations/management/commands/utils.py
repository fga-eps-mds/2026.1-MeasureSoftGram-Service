import contextlib
import datetime as dt
import random

from django.db.utils import IntegrityError
from django.utils import timezone

from characteristics.models import BalanceMatrix, SupportedCharacteristic
from release_configuration.models import ReleaseConfiguration
from subcharacteristics.models import SupportedSubCharacteristic
from utils import exceptions, staticfiles


def create_supported_characteristics(suported_characteristics):
    for characteristic in suported_characteristics:
        with contextlib.suppress(IntegrityError):
            klass = SupportedCharacteristic

            charact, _ = klass.objects.get_or_create(
                name=characteristic['name'],
                key=characteristic['key'],
            )

            subcharacteristics_keys = [
                subcharacteristic['key']
                for subcharacteristic in characteristic['subcharacteristics']
            ]

            subcharacteristics = SupportedSubCharacteristic.objects.filter(
                key__in=subcharacteristics_keys,
            )

            if subcharacteristics.count() != len(subcharacteristics_keys):
                raise exceptions.MissingSupportedSubCharacteristicError()

            charact.subcharacteristics.set(subcharacteristics)


def create_balance_matrix(
    suported_characteristics: list[SupportedCharacteristic],
):
    filtered_balance_matrix = {
        characteristic.key: characteristic
        for characteristic in suported_characteristics
    }
    to_create = []
    for (
        source_characteristic,
        relations,
    ) in staticfiles.DEFAULT_BALANCE_MATRIX.items():
        to_create.extend(
            [
                BalanceMatrix(
                    source_characteristic=filtered_balance_matrix.get(
                        source_characteristic
                    ),
                    target_characteristic=filtered_balance_matrix.get(
                        target_characteristic
                    ),
                    relation_type=relation,
                )
                for relation in ['-', '+']
                for target_characteristic in relations.get(relation, [])
                if source_characteristic in filtered_balance_matrix
                and target_characteristic in filtered_balance_matrix
            ]
        )
    BalanceMatrix.objects.bulk_create(to_create)


def force_the_sum_to_equal_100(entities_data: dict):
    weight_sum = sum(entity['weight'] for entity in entities_data)

    if weight_sum != 100:
        entity = random.choice(entities_data)
        entity['weight'] += 100 - weight_sum

    return entities_data


def get_measures(subcharacteristic: SupportedSubCharacteristic):
    measures = subcharacteristic.measures.all()
    weight = 100 // measures.count()
    data = [{'key': measure.key, 'weight': weight} for measure in measures]
    data = force_the_sum_to_equal_100(data)
    return data


def get_subcharacteristics(characteristic: SupportedCharacteristic):
    data = []

    subcharacteristics = characteristic.subcharacteristics.all()

    weight = 100 // subcharacteristics.count()

    for subcharacteristic in subcharacteristics:
        data.append(
            {
                'key': subcharacteristic.key,
                'weight': weight,
                'measures': get_measures(subcharacteristic),
            }
        )

    data = force_the_sum_to_equal_100(data)

    return data


def create_a_releaseconfig(characteristics_keys, product):
    """
    Função que gera uma pré-configuração com pesos divididos
    igualmente com base nas características passadas no parâmetro.

    Observação: A pré-configuração utiliza todoas as subcaracterísticas,
    medidas e métricas associadas com a arvore das características.
    """
    characteristics = SupportedCharacteristic.objects.filter(
        key__in=characteristics_keys,
    )

    weight = 100 // characteristics.count()

    data = []
    for characteristic in characteristics:
        data.append(
            {
                'key': characteristic.key,
                'weight': weight,
                'subcharacteristics': get_subcharacteristics(characteristic),
            }
        )

    data = force_the_sum_to_equal_100(data)
    release_config = {'characteristics': data}

    release_config = ReleaseConfiguration.objects.create(
        name='custom release-config',
        data=release_config,
        product=product,
    )

    return release_config


def get_random_start_at():
    return timezone.now() - dt.timedelta(days=random.randint(1, 90))


def get_random_end_at():
    return timezone.now() + dt.timedelta(days=random.randint(1, 90))


def get_random_changes(characteristics_keys):
    changes = []
    for _ in range(random.randint(5, 15)):
        changes.append(
            {
                'characteristic_key': random.choice(characteristics_keys),
                'delta': random.randint(-50, 50),
            }
        )
    return changes


def get_random_goal_data(pre_config: ReleaseConfiguration):
    """
    Função que gera um objetivo aleatório com base na pré-configuração passada
    no parâmetro.
    """
    characteristics_keys = [
        obj['key'] for obj in pre_config.data['characteristics']
    ]

    major = random.randint(0, 9)
    minor = random.randint(0, 9)
    patch = random.randint(0, 9)

    return {
        'release_name': f'v{major}.{minor}.{patch}',
        'start_at': get_random_start_at(),
        'end_at': get_random_end_at(),
        'changes': get_random_changes(characteristics_keys),
    }
