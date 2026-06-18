from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient

from characteristics.models import BalanceMatrix, CalculatedCharacteristic, SupportedCharacteristic
from characteristics.serializers import BalanceMatrixSerializer
from utils.tests import APITestCaseExpanded


class BalanceMatrixViewSetTest(APITestCase):
    def setUp(self):
        # Create test data
        characteristic1 = SupportedCharacteristic.objects.create(
            key='characteristic1'
        )
        characteristic2 = SupportedCharacteristic.objects.create(
            key='characteristic2'
        )
        characteristic3 = SupportedCharacteristic.objects.create(
            key='characteristic3'
        )

        BalanceMatrix.objects.create(
            source_characteristic=characteristic1,
            target_characteristic=characteristic2,
            relation_type='+',
        )
        BalanceMatrix.objects.create(
            source_characteristic=characteristic2,
            target_characteristic=characteristic1,
            relation_type='+',
        )
        BalanceMatrix.objects.create(
            source_characteristic=characteristic1,
            target_characteristic=characteristic3,
            relation_type='-',
        )
        BalanceMatrix.objects.create(
            source_characteristic=characteristic3,
            target_characteristic=characteristic1,
            relation_type='-',
        )

    def test_list_balance_matrix(self):
        url = '/api/v1/balance-matrix/'

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        expected_data = {
            'count': 3,
            'next': None,
            'previous': None,
            'result': {
                'characteristic1': {
                    '+': ['characteristic2'],
                    '-': ['characteristic3'],
                },
                'characteristic2': {'+': ['characteristic1'], '-': []},
                'characteristic3': {'+': [], '-': ['characteristic1']},
            },
        }

        self.assertEqual(response.json(), expected_data)


class LatestCalculatedCharacteristicBadgeViewSetTest(APITestCaseExpanded):
    """Tests for the public SVG badge endpoint for characteristics."""

    def setUp(self):
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        self.client = APIClient()
        self.characteristic = SupportedCharacteristic.objects.first()

    def _get_badge_url(self, key=None):
        key = key or self.characteristic.key
        return (
            f'/api/v1/organizations/{self.org.id}/'
            f'products/{self.product.id}/'
            f'repositories/{self.repository.id}/'
            f'latest-values/characteristics/{key}/badge/'
        )

    def _create_calculated_characteristic(self, value, characteristic=None):
        char = characteristic or self.characteristic
        return CalculatedCharacteristic.objects.create(
            characteristic=char,
            value=value,
            repository=self.repository,
        )

    def test_badge_returns_svg_content_type(self):
        self._create_calculated_characteristic(0.85)
        response = self.client.get(self._get_badge_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_badge_no_authentication_required(self):
        self._create_calculated_characteristic(0.5)
        response = self.client.get(self._get_badge_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_badge_grade_a(self):
        self._create_calculated_characteristic(0.90)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)
        self.assertIn('#4c1', content)

    def test_badge_grade_b(self):
        self._create_calculated_characteristic(0.70)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>B<', content)
        self.assertIn('#97CA00', content)

    def test_badge_grade_c(self):
        self._create_calculated_characteristic(0.50)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>C<', content)
        self.assertIn('#dfb317', content)

    def test_badge_grade_d(self):
        self._create_calculated_characteristic(0.30)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>D<', content)
        self.assertIn('#fe7d37', content)

    def test_badge_grade_e(self):
        self._create_calculated_characteristic(0.10)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>E<', content)
        self.assertIn('#e05d44', content)

    def test_badge_no_calculated_characteristic_returns_na(self):
        response = self.client.get(self._get_badge_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        self.assertIn('N/A', content)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_badge_contains_characteristic_name(self):
        self._create_calculated_characteristic(0.75)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn(self.characteristic.name, content)

    def test_badge_invalid_characteristic_returns_404(self):
        response = self.client.get(self._get_badge_url(key='nonexistent_key'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(BADGE_STALENESS_DAYS=30)
    def test_badge_stale_characteristic_returns_na(self):
        calc = self._create_calculated_characteristic(0.90)
        calc.created_at = timezone.now() - timedelta(days=31)
        calc.save()
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('N/A', content)

    @override_settings(BADGE_STALENESS_DAYS=30)
    def test_badge_fresh_characteristic_returns_grade(self):
        calc = self._create_calculated_characteristic(0.90)
        calc.created_at = timezone.now() - timedelta(days=29)
        calc.save()
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)
    @override_settings(BADGE_STALENESS_DAYS=0)
    def test_badge_staleness_disabled_with_zero(self):
        calc = self._create_calculated_characteristic(0.90)
        calc.created_at = timezone.now() - timedelta(days=365)
        calc.save()
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)
    @override_settings(BADGE_STALENESS_DAYS=None)
    def test_badge_staleness_disabled_with_none(self):
        calc = self._create_calculated_characteristic(0.90)
        calc.created_at = timezone.now() - timedelta(days=365)
        calc.save()
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)
