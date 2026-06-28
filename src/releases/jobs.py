from resources import calculate_characteristics

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.db import connection
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

# Chave fixa do advisory lock de sessao do Postgres usado para eleger um
# unico worker como dono do scheduler. Qualquer int de 64 bits estavel
# serve, contanto que seja o mesmo em todos os workers do mesmo banco.
SCHEDULER_ADVISORY_LOCK_KEY = 728_945_113


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


def acquire_scheduler_lock():
    """Tenta adquirir o advisory lock de sessao do scheduler.

    Com gunicorn multi-worker, releases/apps.py ready() roda uma vez por
    worker. Sem eleicao de lider, cada worker sobe seu proprio
    BackgroundScheduler e o cron dispara N vezes (uma por worker),
    duplicando CalculatedCharacteristic.

    pg_try_advisory_lock retorna True para o primeiro worker (que vira o
    dono do scheduler) e False para os demais, sem bloquear. O lock e de
    sessao: enquanto a conexao do worker dono viver, ele segura o lock.

    Retorna True se este worker deve startar o scheduler, False caso
    contrario. Em bancos que nao suportam advisory lock (ex: sqlite em
    cenarios fora de producao) cai no fallback de startar (retorna True),
    preservando o comportamento single-process historico.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_try_advisory_lock(%s)',
                [SCHEDULER_ADVISORY_LOCK_KEY],
            )
            row = cursor.fetchone()
            return bool(row[0]) if row else False
    except Exception:
        # Banco sem suporte a advisory lock: mantem comportamento antigo.
        # Em prod com >1 worker, use GUNICORN_WORKERS=1 no container do
        # scheduler como fallback (ver start_service.sh / deploy).
        return True


def check_the_need_to_calculate_releases():
    if not acquire_scheduler_lock():
        print(
            'Scheduler ja iniciado por outro worker, ignorando...',
            file=sys.stdout,
        )
        return

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
