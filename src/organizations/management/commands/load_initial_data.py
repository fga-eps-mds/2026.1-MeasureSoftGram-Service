# Python Imports
import contextlib
import datetime as dt
import logging
import os

# 3rd Party Imports
import requests
from django.conf import settings

# Django Imports
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.utils import IntegrityError
from django.utils import timezone

import utils
from characteristics.models import (
    CalculatedCharacteristic,
    SupportedCharacteristic,
)
from math_model.services import MathModelServices
from goals.serializers import GoalSerializer
from measures.models import CalculatedMeasure, SupportedMeasure
from metrics.models import CollectedMetric, SupportedMetric
from organizations.models import Organization, Product, Repository
from release_configuration.models import ReleaseConfiguration
from staticfiles import SUPPORTED_MEASURES
from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)
from tsqmi.models import TSQMI
from utils import namefy

# Local Imports
from utils import (
    exceptions,
    get_random_datetime,
    get_random_path,
    get_random_qualifier,
    get_random_value,
    staticfiles,
)

from .utils import (
    create_balance_matrix,
    create_supported_characteristics,
    get_random_goal_data,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Registra os dados iniciais no banco de dados'

    def add_arguments(self, parser):
        # Create fake data
        parser.add_argument(
            '--fake-data',
            type=bool,
            default=False,
            help='Create fake data',
        )

    def create_suported_measures(self):
        """
        Função que popula banco de dados com todas as medidas que são
        suportadas atualmente e as métricas que cada medida é dependente
        """
        for measure_data in SUPPORTED_MEASURES:
            measure_key = list(measure_data.keys())[0]
            with contextlib.suppress(IntegrityError):
                measure_name = utils.namefy(measure_key)

                measure, _ = SupportedMeasure.objects.get_or_create(
                    key=measure_key,
                    name=measure_name,
                )

                logger.info(f'Creating supported measure {measure_key}')

                metrics_keys = {
                    metric for metric in measure_data[measure_key]['metrics']
                }

                metrics = SupportedMetric.objects.filter(
                    key__in=metrics_keys,
                )

                if metrics.count() != len(metrics_keys):
                    raise exceptions.MissingSupportedMetricException()

                measure.metrics.set(metrics)
                logger.info(
                    (
                        f"Metrics {','.join(metrics_keys)} "
                        f'were associated to {measure_key}'
                    )
                )

    def create_github_suported_measures(self):
        """
        Função que popula banco de dados com todas as medidas que são
        suportadas atualmente e as métricas que cada medida é dependente
        """
        for measure_data in settings.GITHUB_SUPPORTED_MEASURES:
            measure_key = list(measure_data.keys())[0]
            with contextlib.suppress(IntegrityError):
                measure_name = utils.namefy(measure_key)

                measure, _ = SupportedMeasure.objects.get_or_create(
                    key=measure_key,
                    name=measure_name,
                )

                logger.info(f'Creating supported measure {measure_key}')

                metrics_keys = {
                    metric for metric in measure_data[measure_key]['metrics']
                }

                metrics = SupportedMetric.objects.filter(
                    key__in=metrics_keys,
                )

                if metrics.count() != len(metrics_keys):
                    raise exceptions.MissingSupportedMetricException()

                measure.metrics.set(metrics)
                logger.info(
                    (
                        f"Metrics {','.join(metrics_keys)} "
                        f'were associated to {measure_key}'
                    )
                )

    def create_supported_metrics(self):
        self.create_sonarqube_supported_metrics()
        self.create_github_supported_metrics()

    def create_sonarqube_supported_metrics(self):
        data = staticfiles.SONARQUBE_AVAILABLE_METRICS

        sonar_metrics = [
            SupportedMetric(
                key=metric['key'],
                name=metric['name'],
                metric_type=metric['metric_type']
            )
            for metric in data
        ]
        for metric in sonar_metrics:
            with contextlib.suppress(IntegrityError):
                metric.save()

    def create_github_supported_metrics(self):
        github_metrics = [
            SupportedMetric(
                key=metric['key'],
                name=metric['name'],
                metric_type=metric['metric_type'],
            )
            for metric in staticfiles.GITHUB_AVAILABLE_METRICS
        ]

        for metric in github_metrics:
            with contextlib.suppress(IntegrityError):
                metric.save()

    def model_generator(self, model, metrics):
        for metric in metrics:
            with contextlib.suppress(IntegrityError):
                model.objects.create(
                    key=metric['key'],
                    name=metric['name'],
                    description=metric.get('description', ''),
                    metric_type=metric['type'],
                )

    def create_fake_calculated_entity(
        self,
        qs,
        calculated_entity_factory,
        bulk_create_klass,
        get_entity_qty,
    ):
        if self.fake_data is False and settings.CREATE_FAKE_DATA is False:
            return

        end_date = timezone.now()
        start_date = end_date - dt.timedelta(days=90)

        MIN_NUMBER_OF_CALCULATED_ENTITIES = 50
        MIN_NUMBER = MIN_NUMBER_OF_CALCULATED_ENTITIES

        fake_calculated_entities = []

        for entity in qs:
            qty = get_entity_qty(entity)

            if qty < MIN_NUMBER:
                for _ in range(MIN_NUMBER - qty):
                    created_at = get_random_datetime(start_date, end_date)
                    fake_calculated_entities.append(
                        calculated_entity_factory(entity, created_at),
                    )

        bulk_create_klass.objects.bulk_create(fake_calculated_entities)

    def create_fake_collected_metrics(self, repository):
        qs = SupportedMetric.objects.all()

        def calculated_entity_factory(entity, created_at):
            metric_type = entity.metric_type
            value = get_random_value(metric_type)

            return CollectedMetric(
                metric=entity,
                path=get_random_path(),
                qualifier=get_random_qualifier(),
                value=value,
                created_at=created_at,
                repository=repository,
            )

        def get_entity_qty(entity):
            return entity.collected_metrics.filter(
                repository=repository,
            ).count()

        self.create_fake_calculated_entity(
            qs,
            calculated_entity_factory,
            CollectedMetric,
            get_entity_qty,
        )

    def create_fake_calculated_measures(self, repository):
        qs = SupportedMeasure.objects.all()

        def calculated_entity_factory(entity, created_at):
            return CalculatedMeasure(
                measure=entity,
                value=get_random_value('PERCENT'),
                created_at=created_at,
                repository=repository,
            )

        def get_entity_qty(entity):
            return entity.calculated_measures.filter(
                repository=repository,
            ).count()

        self.create_fake_calculated_entity(
            qs,
            calculated_entity_factory,
            CalculatedMeasure,
            get_entity_qty,
        )

    def create_supported_subcharacteristics(self):
        supported_subcharacteristics = [
            {
                'key': 'modifiability',
                'name': 'Modifiability',
                'measures': [
                    {'key': 'duplication_absense'},
                    {'key': 'commented_file_density'},
                    {'key': 'non_complex_file_density'},
                ],
            },
            {
                'key': 'testing_status',
                'name': 'Testing Status',
                'measures': [
                    {'key': 'test_coverage'},
                    {'key': 'test_builds'},
                    {'key': 'passed_tests'},
                ],
            },
            {
                "key": "functional_completeness",
                "name": "Functional Completeness",
                "measures": [
                    {"key": "team_throughput"},
                ],
            },
            {
                "key": "maturity",
                "name": "Maturity",
                "measures": [
                    {"key": "ci_feedback_time"},
                ],
            },
        ]

        for subcharacteristic in supported_subcharacteristics:
            with contextlib.suppress(IntegrityError):
                klass = SupportedSubCharacteristic

                sub_char, _ = klass.objects.get_or_create(
                    name=subcharacteristic['name'],
                    key=subcharacteristic['key'],
                )

                measures_keys = [
                    measure['key'] for measure in subcharacteristic['measures']
                ]

                measures = SupportedMeasure.objects.filter(
                    key__in=measures_keys,
                )

                if measures.count() != len(measures_keys):
                    raise exceptions.MissingSupportedMeasureException()

                sub_char.measures.set(measures)

    def create_supported_characteristics(self):
        supported_characteristics = [
            {
                'key': 'reliability',
                'name': 'Reliability',
                'subcharacteristics': [
                    {'key': 'testing_status'},
                    {'key': 'maturity'},
                ],
            },
            {
                'key': 'maintainability',
                'name': 'Maintainability',
                'subcharacteristics': [
                    {'key': 'modifiability'},
                ],
            },
            {
                "key": "functional_suitability",
                "name": "Functional Suitability",
                "subcharacteristics": [
                    {"key": "functional_completeness"},
                ]
            },
        ]
        create_supported_characteristics(supported_characteristics)

    def create_balance_matrix(self):
        characteristics = SupportedCharacteristic.objects.all()
        create_balance_matrix(characteristics)

    def create_fake_calculated_characteristics(self, repository):
        qs = SupportedCharacteristic.objects.annotate(
            qty=Count('calculated_characteristics'),
        )

        def calculated_entity_factory(entity, created_at):
            return CalculatedCharacteristic(
                characteristic=entity,
                value=get_random_value('PERCENT'),
                created_at=created_at,
                repository=repository,
            )

        def get_entity_qty(entity):
            return entity.calculated_characteristics.filter(
                repository=repository,
            ).count()

        self.create_fake_calculated_entity(
            qs,
            calculated_entity_factory,
            CalculatedCharacteristic,
            get_entity_qty,
        )

    def create_fake_calculated_subcharacteristics(self, repository):
        qs = SupportedSubCharacteristic.objects.annotate(
            qty=Count('calculated_subcharacteristics'),
        )

        def calculated_entity_factory(entity, created_at):
            return CalculatedSubCharacteristic(
                subcharacteristic=entity,
                value=get_random_value('PERCENT'),
                created_at=created_at,
                repository=repository,
            )

        def get_entity_qty(entity):
            return entity.calculated_subcharacteristics.filter(
                repository=repository,
            ).count()

        self.create_fake_calculated_entity(
            qs,
            calculated_entity_factory,
            CalculatedSubCharacteristic,
            get_entity_qty,
        )

    def create_default_pre_config(self, product):
        ReleaseConfiguration.objects.get_or_create(
            name='Default pre-config',
            data=staticfiles.DEFAULT_PRE_CONFIG,
            product=product,
        )

    def create_a_goal(self, product: Product):
        pre_config = product.release_configuration.first()
        data = get_random_goal_data(pre_config)
        serializer = GoalSerializer(data=data)

        class MockView:
            @staticmethod
            def get_product():
                return product

        serializer.context['view'] = MockView
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)

    def create_fake_tsqmi_data(self, repository):
        if self.fake_data is False and settings.CREATE_FAKE_DATA is False:
            return

        qs = TSQMI.objects.filter(repository=repository)

        MIN_NUMBER = 50

        if qs.count() >= MIN_NUMBER:
            return

        TSQMI.objects.bulk_create(
            [
                TSQMI(
                    value=get_random_value('PERCENT'),
                    repository=repository,
                )
                for _ in range(MIN_NUMBER - qs.count())
            ]
        )

    def create_fake_organizations(self):
        organizations = [
            Organization(
                name='fga-eps-mds',
                description=(
                    (
                        'Organização que agrupa os '
                        'projetos de EPS e MDS da FGA.'
                    )
                ),
            ),
            Organization(
                name='UnBArqDsw2021',
                description=(
                    (
                        'Organização que agrupa os '
                        'projetos de Arquitetura e Desenvolvimento de '
                        'Software do semestre 2021.01'
                    )
                ),
            ),
            Organization(
                name='IHC-FGA-2020',
                description=(
                    (
                        'Organização que agrupa os projetos da disciplina de '
                        'Interação Humano Computador'
                    )
                ),
            ),
        ]

        for organization in organizations:
            if Organization.objects.filter(name=organization.name).exists():
                continue
            organization.save()

    def create_fake_products(self):
        organizations = Organization.objects.all()

        organizations = {
            organization.name: organization for organization in organizations
        }

        products = [
            Product(
                name='Animalesco',
                description=(
                    'Uma aplicação para realizar o controle e '
                    'acompanhamento para com a saúde dos pets. '
                    'Os usuários, após se registrarem, podem '
                    'realizar o cadastro dos seus pets e a partir '
                    'disso fazer o acompanhamento do bichinho de '
                    'maneira digital.'
                ),
                organization=organizations['UnBArqDsw2021'],
            ),
            Product(
                name='BCE UnB',
                description=(
                    'Este projeto possui o objetivo de analisar o '
                    'site da BCE, se propondo a sugerir melhorias '
                    'nos serviços de empréstimo de livros, '
                    'com base nos conceitos aprendidos na '
                    'discplina de IHC.'
                ),
                organization=organizations['IHC-FGA-2020'],
            ),
            Product(
                name='MeasureSoftGram',
                description=(
                    'Este projeto que visa a construção de um '
                    'sistema de análise quantitativa da qualidade '
                    'de um sistema de software.'
                ),
                organization=organizations['fga-eps-mds'],
            ),
            Product(
                name='Acacia',
                description=(
                    'Este projeto que visa a construção de um '
                    'sistema de colaboração de colheita de '
                    'árvores frutíferas em ambiente urbano.'
                ),
                organization=organizations['fga-eps-mds'],
            ),
        ]

        for product in products:
            if Product.objects.filter(
                name=product.name,
                organization=product.organization,
            ).exists():
                continue
            product.save()

    def create_fake_repositories(self):
        products = Product.objects.all()

        products = {product.name: product for product in products}

        repositories = [
            Repository(
                name='2019.2-Acacia',
                description=('Repositório do backend do projeto Acacia.'),
                product=products['Acacia'],
            ),
            Repository(
                name='2019.2-Acacia-Frontend',
                description=('Repositório do frontend do projeto Acacia.'),
                product=products['Acacia'],
            ),
            Repository(
                name='2019.2-Acacia-Frontend',
                description=('Repositório do frontend do projeto Acacia.'),
                product=products['Acacia'],
            ),
            Repository(
                name='2020.1-BCE',
                description=('Repositório do projeto BCE UnB.'),
                product=products['BCE UnB'],
            ),
            Repository(
                name='2021.1_G01_Animalesco_BackEnd',
                description=('Repositório do backend do projeto Animalesco.'),
                product=products['Animalesco'],
            ),
            Repository(
                name='2021.1_G01_Animalesco_FrontEnd',
                description=(
                    'Repositório do frontend ' 'do projeto Animalesco.'
                ),
                product=products['Animalesco'],
            ),
            Repository(
                name='2022-1-MeasureSoftGram-Service',
                description=(
                    'Repositório do backend do projeto ' 'MeasureSoftGram.'
                ),
                product=products['MeasureSoftGram'],
            ),
            Repository(
                name='2022-1-MeasureSoftGram-Core',
                description=(
                    'Repositório da API do modelo matemático '
                    'do projeto MeasureSoftGram'
                ),
                product=products['MeasureSoftGram'],
            ),
            Repository(
                name='2022-1-MeasureSoftGram-Front',
                description=(
                    'Repositório do frontend da projeto ' 'MeasureSoftGram'
                ),
                product=products['MeasureSoftGram'],
            ),
            Repository(
                name='2022-1-MeasureSoftGram-CLI',
                description=(
                    'Repositório do CLI da projeto ' 'MeasureSoftGram'
                ),
                product=products['MeasureSoftGram'],
            ),
        ]

        for repository in repositories:
            if Repository.objects.filter(
                name=repository.name,
                product=repository.product,
            ).exists():
                continue
            repository.save()

    def handle(self, *args, **kwargs):
        self.fake_data = kwargs.get('fake_data')

        User = get_user_model()
        with contextlib.suppress(IntegrityError):
            User.objects.create_superuser(
                username=os.getenv('SUPERADMIN_USERNAME', 'admin'),
                email=os.getenv('SUPERADMIN_EMAIL', 'admin@admin.com'),
                password=os.getenv('SUPERADMIN_PASSWORD', 'admin'),
            )

        self.create_supported_metrics()
        self.create_suported_measures()
        self.create_github_suported_measures()
        self.create_supported_subcharacteristics()
        self.create_supported_characteristics()
        self.create_balance_matrix()
        self.create_fake_organizations()
        self.create_fake_products()
        self.create_fake_repositories()

        repositories = Repository.objects.all()

        if settings.CREATE_FAKE_DATA or self.fake_data:
            for repository in repositories:
                self.create_fake_collected_metrics(repository)
                self.create_fake_calculated_measures(repository)
                self.create_fake_calculated_subcharacteristics(repository)
                self.create_fake_calculated_characteristics(repository)
                self.create_fake_tsqmi_data(repository)

        products = Product.objects.all()

        for product in products:
            self.create_a_goal(product)
