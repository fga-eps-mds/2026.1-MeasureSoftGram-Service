from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from tsqmi.models import TSQMI
from utils.tests import APITestCaseExpanded


class LatestCalculatedTSQMIBadgeViewSetTest(APITestCaseExpanded):
    """Tests for the public SVG badge endpoint."""

    def setUp(self):
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        self.client = APIClient()

    def _get_badge_url(self):
        return reverse(
            'latest-calculated-tsqmi-badge-list',
            args=[self.org.id, self.product.id, self.repository.id],
        )

    def _create_tsqmi(self, value):
        return TSQMI.objects.create(
            value=value,
            repository=self.repository,
        )

    def test_badge_returns_svg_content_type(self):
        self._create_tsqmi(0.85)
        response = self.client.get(self._get_badge_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_badge_no_authentication_required(self):
        """Badge endpoint must be public (no auth required)."""
        self._create_tsqmi(0.5)
        response = self.client.get(self._get_badge_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_badge_grade_a(self):
        self._create_tsqmi(0.90)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)
        self.assertIn('#4c1', content)

    def test_badge_grade_b(self):
        self._create_tsqmi(0.70)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>B<', content)
        self.assertIn('#97CA00', content)

    def test_badge_grade_c(self):
        self._create_tsqmi(0.50)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>C<', content)
        self.assertIn('#dfb317', content)

    def test_badge_grade_d(self):
        self._create_tsqmi(0.30)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>D<', content)
        self.assertIn('#fe7d37', content)

    def test_badge_grade_e(self):
        self._create_tsqmi(0.10)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>E<', content)
        self.assertIn('#e05d44', content)

    def test_badge_boundary_080_is_grade_a(self):
        self._create_tsqmi(0.80)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)

    def test_badge_boundary_060_is_grade_b(self):
        self._create_tsqmi(0.60)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>B<', content)

    def test_badge_boundary_040_is_grade_c(self):
        self._create_tsqmi(0.40)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>C<', content)

    def test_badge_boundary_020_is_grade_d(self):
        self._create_tsqmi(0.20)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>D<', content)

    def test_badge_no_tsqmi_returns_na(self):
        """When no TSQMI has been calculated, return N/A badge."""
        response = self.client.get(self._get_badge_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        self.assertIn('N/A', content)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_badge_contains_measuresoftgram_label(self):
        self._create_tsqmi(0.75)
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('MeasureSoftGram', content)

    @override_settings(BADGE_STALENESS_DAYS=30)
    def test_badge_stale_tsqmi_returns_na(self):
        """When the latest TSQMI is older than BADGE_STALENESS_DAYS, return N/A."""
        tsqmi = self._create_tsqmi(0.90)
        tsqmi.created_at = timezone.now() - timedelta(days=31)
        tsqmi.save()
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('N/A', content)

    @override_settings(BADGE_STALENESS_DAYS=30)
    def test_badge_fresh_tsqmi_returns_grade(self):
        """When the latest TSQMI is recent, return the grade normally."""
        tsqmi = self._create_tsqmi(0.90)
        tsqmi.created_at = timezone.now() - timedelta(days=29)
        tsqmi.save()
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)

    @override_settings(BADGE_STALENESS_DAYS=0)
    def test_badge_staleness_disabled_with_zero(self):
        """When BADGE_STALENESS_DAYS=0, staleness check is disabled."""
        tsqmi = self._create_tsqmi(0.90)
        tsqmi.created_at = timezone.now() - timedelta(days=365)
        tsqmi.save()
        response = self.client.get(self._get_badge_url())
        content = response.content.decode()
        self.assertIn('>A<', content)



