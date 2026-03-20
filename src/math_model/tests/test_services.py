from math_model.services import MathModelServices
from utils.tests import APITestCaseExpanded
from utils import staticfiles
from release_configuration.models import ReleaseConfiguration
from release_configuration.serializers import ReleaseConfigurationSerializer
from metrics.models import SupportedMetric, CollectedMetric
from freezegun import freeze_time
from measures.models import SupportedMeasure, CalculatedMeasure
from subcharacteristics.models import SupportedSubCharacteristic, CalculatedSubCharacteristic
from characteristics.models import CalculatedCharacteristic, SupportedCharacteristic
from math_model import utils
import dicts


@freeze_time("2024-09-08 20:00:00")
class MathModelServicesTest(APITestCaseExpanded):
    def setUp(self):
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        ReleaseConfiguration.objects.get_or_create(
            name='Default pre-config',
            data=staticfiles.DEFAULT_PRE_CONFIG,
            product=self.product,
        )
        self.release_config = self.product.release_configuration.first()
        self.services = MathModelServices(self.repository, self.product)

    def test_if_parse_release_config(self):
        config_serializer = ReleaseConfigurationSerializer(self.release_config)
        char_keys, subchar_keys, measure_keys = utils.parse_release_configuration(config_serializer.data)
        assert char_keys == ['reliability', 'maintainability', 'functional_suitability']
        assert subchar_keys == ['testing_status', 'maturity', 'modifiability', 'functional_completeness']
        assert measure_keys == [
            'passed_tests',
            'test_builds',
            'test_coverage',
            'ci_feedback_time',
            'non_complex_file_density',
            'commented_file_density',
            'duplication_absense',
            'team_throughput'
        ]

    def test_if_calculate_measures_is_working(self):
        listed_values = [
            'coverage',
            'complexity',
            'functions',
            'comment_lines_density',
            'duplicated_lines_density',
        ]

        uts_values = ['test_execution_time', 'tests']
        trk_values = ['test_failures', 'test_errors']

        for values, qualifier in zip(
            [listed_values, uts_values, trk_values], ['FIL', 'UTS', 'TRK']
        ):
            for metric in SupportedMetric.objects.filter(key__in=values):
                CollectedMetric.objects.create(
                    value=0.1,
                    metric=metric,
                    repository=self.repository,
                    qualifier=qualifier,
                )
                CollectedMetric.objects.create(
                    value=0.2,
                    metric=metric,
                    repository=self.repository,
                    qualifier=qualifier,
                )

        listed_values = [
            'total_issues',
            'resolved_issues',
            'sum_ci_feedback_times',
            'total_builds',
        ]
        for values, qualifier in zip(
            [listed_values], ['FIL']
        ):
            for metric in SupportedMetric.objects.filter(key__in=values):
                CollectedMetric.objects.create(
                    value=1,
                    metric=metric,
                    repository=self.repository,
                    qualifier=qualifier,
                )
        measures_keys = [

            measure.key for measure in SupportedMeasure.objects.all()
        ]
        calculated_measures = self.services.calculate_measures(
            measure_keys=measures_keys,
            release_configuration=self.release_config
        )
        assert calculated_measures == dicts.MEASURE_RESPONSE

    def test_if_calculate_subcharacteristics_is_working(self):

        qs = self.release_config.get_subcharacteristics_qs()

        for measure in SupportedMeasure.objects.all():
            CalculatedMeasure.objects.create(
                value=0.1, measure=measure, repository=self.repository
            )

        keys = [subcharacteristic.key for subcharacteristic in qs]
        subchar = self.services.calculate_sucharacteristics(
            subcharacteristics_keys=keys,
            release_configuration=self.release_config
        )
        assert subchar == dicts.SUBCHAR_RESPONSE

    def test_if_calculate_characteristics_is_working(self):
        qs = self.release_config.get_characteristics_qs()

        for sub_char in SupportedSubCharacteristic.objects.all():
            CalculatedSubCharacteristic.objects.create(
                value=0.1,
                subcharacteristic=sub_char,
                repository=self.repository,
            )

        keys = [characteristic.key for characteristic in qs]
        char = self.services.calculcate_characterisctics(
            characteristics_keys=keys,
            release_configuration=self.release_config
        )
        assert char == dicts.CHAR_RESPONSE

    def test_if_calculate_tsqmi_is_working(self):
        for char in SupportedCharacteristic.objects.all():
            CalculatedCharacteristic.objects.create(
                value=0.1, characteristic=char, repository=self.repository
            )

        tsqmi = self.services.calculate_tsqmi(self.release_config)
        assert tsqmi == {'id': 1, 'value': 0.1, 'created_at': '2024-09-08T17:00:00-03:00'}
