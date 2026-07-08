# Python Imports
import contextlib
import logging
import os

# 3rd Party Imports
from django.conf import settings

# Django Imports
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

import utils
from characteristics.models import SupportedCharacteristic
from measures.models import SupportedMeasure
from metrics.models import SupportedMetric
from organizations.services import seed_demo_data
from release_configuration.models import ReleaseConfiguration
from staticfiles import SUPPORTED_MEASURES
from subcharacteristics.models import SupportedSubCharacteristic
from utils import namefy

# Local Imports
from utils import (
    exceptions,
    staticfiles,
)

from .utils import (
    create_balance_matrix,
    create_supported_characteristics,
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

    def create_default_pre_config(self, product):
        ReleaseConfiguration.objects.get_or_create(
            name='Default pre-config',
            data=staticfiles.DEFAULT_PRE_CONFIG,
            product=product,
        )

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

        if settings.CREATE_FAKE_DATA or self.fake_data:
            superadmin = User.objects.get(
                username=os.getenv('SUPERADMIN_USERNAME', 'admin'),
            )
            seed_demo_data(superadmin)
