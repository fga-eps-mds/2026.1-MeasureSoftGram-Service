from resources import calculate_characteristics

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.utils import timezone
from django_apscheduler.models import DjangoJobExecution

from releases.models import Release
from organizations.models import Repository
from organizations.models import Product
from characteristics.models import (
    CalculatedCharacteristic,
    SupportedCharacteristic,
)

import sys


def get_releases_and_create_results():
    today = timezone.now()
    today_min = today.replace(hour=0, minute=0, second=0, microsecond=0)
    today_max = today.replace(hour=23, minute=59, second=59, microsecond=59)

    releases = Release.objects.filter(
        end_at__lte=today_max, end_at__gte=today_min
    ).all()

    if len(releases) == 0:
        return

    for release in releases:
        repositories = Repository.objects.filter(
            product_id=release.product_id  # type: ignore
        ).all()

        for repository in repositories:
            product = Product.objects.filter(
                id=repository.product_id
            ).first()   # type: ignore

            data_characteristics = {
                'characteristics': [
                    {'key': 'reliability'},
                    {'key': 'maintainability'},
                ]
            }

            characteristics_keys = [
                characteristic['key']
                for characteristic in data_characteristics['characteristics']
            ]

            qs = SupportedCharacteristic.objects.filter(
                key__in=characteristics_keys
            ).prefetch_related(
                'subcharacteristics',
                'subcharacteristics__calculated_subcharacteristics',
            )

            pre_config = product.release_configuration.first()   # type: ignore

            core_params = {'characteristics': []}

            char: SupportedCharacteristic
            for char in qs:
                subchars_params = char.get_latest_subcharacteristics_params(
                    pre_config,
                )

                core_params['characteristics'].append(
                    {
                        'key': char.key,
                        'subcharacteristics': subchars_params,
                    }
                )

            calculate_result = calculate_characteristics(core_params)

            calculated_values = {
                characteristic['key']: characteristic['value']
                for characteristic in calculate_result['characteristics']
            }

            calculated_characteristics = []

            for characteristic in qs:
                value = calculated_values[characteristic.key]

                calculated_characteristics.append(
                    CalculatedCharacteristic(
                        characteristic=characteristic,
                        value=value,
                        repository=repository,
                        created_at=timezone.now(),
                        release=release,
                    )
                )

            try:
                CalculatedCharacteristic.objects.bulk_create(
                    calculated_characteristics
                )
                print('Criou as características calculadas')
            except Exception:
                print('Erro ao criar as características calculadas')
                continue


def check_the_need_to_calculate_releases():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), 'default')

    scheduler.add_job(
        get_releases_and_create_results,
        trigger=CronTrigger(
            hour=00,
            minute=00,
        ),
        name='get_releases_and_create_results',
        jobstore='default',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=10,
        coalesce=True,
        id='get_releases_and_create_results',
    )
    register_events(scheduler)
    scheduler.start()
    print('Scheduler started...', file=sys.stdout)
