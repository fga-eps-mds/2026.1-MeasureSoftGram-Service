from characteristics.models import CalculatedCharacteristic
from releases.models import Release
from core.transformations import norm_diff, diff
import numpy as np


def calculate_diff(planned, accomplished):
    diffs = {}
    planned_values = {item['name']: item['value'] for item in planned}

    for repo in accomplished:
        rp = []
        rd = []
        repo_name = repo['repository_name']

        for characteristic in repo['characteristics']:
            name = characteristic['name']
            value = characteristic['value']
            rd.append(value)

            if name in planned_values:
                rp.append(planned_values[name])

        diff_array = diff(rp, rd)
        diffs[repo_name] = diff_array

        for characteristic, i in zip(repo['characteristics'], range(len(repo['characteristics']))):
            characteristic['diff'] = diffs[repo_name][i]

    return accomplished


def get_planned_values(release: Release):
    planned_values = []

    for characteristic_name, characteristic_value in release.goal.data.items():
        characteristic = {
            'name': characteristic_name,
            'value': characteristic_value / 100,
        }

        planned_values.append(characteristic)

    return planned_values


def get_accomplished_values(release: Release, repositories_ids: list[int]):
    result_calculated = CalculatedCharacteristic.objects.filter(release=release).all().order_by('-created_at')[:2]

    if len(result_calculated) == 0:
        result_calculated = (
            get_calculated_characteristic_by_ids_repositories(
                repositories_ids
            )
        )

    return get_process_calculated_characteristics_to_list(list(result_calculated))


def get_process_calculated_characteristics_to_list(
    result_calculated: list[CalculatedCharacteristic],
):
    accomplished = []
    for calculated_characteristic in result_calculated:

        repository_name = calculated_characteristic.repository.name
        characteristic_name = calculated_characteristic.characteristic.key
        characteristic_value = calculated_characteristic.value

        characteristic = {
            'name': characteristic_name,
            'value': characteristic_value,
        }

        isRepositoryInserted = False

        for repository in accomplished:
            if repository['repository_name'] == repository_name:
                isRepositoryInserted = True
                if all(characteristic['name'] != characteristic_name
                       for characteristic in repository['characteristics']):
                    repository['characteristics'].append(characteristic)

        if not isRepositoryInserted:
            accomplished.append({
                'repository_name': repository_name,
                'characteristics': [characteristic]
            })

    return accomplished


def get_norm_diff(planned_values, accomplished_values):
    for repository in accomplished_values:
        repository['norm_diff'] = calculate_norm_diff(planned_values, repository['characteristics'])

    return accomplished_values


def calculate_norm_diff(planned_values, accomplished_characteristics):
    if len(planned_values) != len(accomplished_characteristics):
        print('The number of planned and accomplished characteristics should be the same.')
        return None

    else:
        rp = []
        rd = []

        for planned_characteristic in planned_values:
            planned_characteristic_name = planned_characteristic['name']

            rp.append(planned_characteristic['value'])
            accomplished_value = None

            for accomplished_characteristic in accomplished_characteristics:
                if accomplished_characteristic['name'] == planned_characteristic_name:
                    accomplished_value = accomplished_characteristic['value']

            if accomplished_value is None:
                print(f'Planned characteristic {planned_characteristic_name}'
                      + 'was not found in the accomplished characteristics.')
                return None

            if accomplished_value < 0 or accomplished_value > 1:
                print('Accomplished characteristic value should be between 0 and 1.')
                return None

            rd.append(accomplished_value)

        return norm_diff(np.array(rp), np.array(rd))


def get_process_calculated_characteristics(

    result_calculated: list[CalculatedCharacteristic],
):
    accomplished = {}
    for calculated_characteristic in result_calculated:
        characteristic = calculated_characteristic.characteristic.key
        repository = calculated_characteristic.repository.name

        if repository not in accomplished:
            accomplished[repository] = {}
        accomplished[repository].update(
            {characteristic: calculated_characteristic.value}
        )
    return accomplished


def get_calculated_characteristic_by_ids_repositories(
    ids_repositories: list[int],
):
    result_calculated = []
    for id_repository in ids_repositories:
        calculated_characteristic = (
            CalculatedCharacteristic.objects.filter(
                repository_id=id_repository, release=None
            )
            .all()
            .order_by('-created_at')[:2]
        )
        result_calculated = result_calculated + list(calculated_characteristic)
    return result_calculated


def get_arrays_diff(goal_data: dict, characteristic_repo: dict):
    array_rp = []
    array_rd = []

    for characteristic in 'reliability', 'maintainability', 'functional_suitability':
        try:
            if (
                goal_data[characteristic]
                and characteristic_repo[characteristic]
            ):
                array_rp.append(goal_data[characteristic] / 100)
                array_rd.append(characteristic_repo[characteristic])
        except Exception:
            continue

    return array_rp, array_rd


def update_release_end_at(release_id: int, new_end_at):
    """
    Atualiza o campo `end_at` de uma Release.

    :param release_id: ID da Release a ser atualizada.
    :param new_end_at: Novo valor para o campo `end_at`.
    :return: A Release atualizada.
    """
    release = Release.objects.get(id=release_id)
    release.end_at = new_end_at
    release.save()

    return release
