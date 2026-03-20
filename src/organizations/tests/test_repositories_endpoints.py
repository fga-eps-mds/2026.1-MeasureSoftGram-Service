import datetime as dt
from unittest import mock
from unittest.mock import patch, Mock
from zoneinfo import ZoneInfo

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from characteristics.models import (
    CalculatedCharacteristic,
    SupportedCharacteristic,
)
from measures.models import CalculatedMeasure, SupportedMeasure
from metrics.models import CollectedMetric, SupportedMetric
from organizations.models import Repository
from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)
from utils.mocks import Mocks
from utils.tests import APITestCaseExpanded
from requests.exceptions import ConnectionError, HTTPError


class PublicRepositoriesViewsSetCase(APITestCaseExpanded):
    def test_unauthenticated_not_allowed(self):
        org = self.get_organization()
        prod = self.get_product(org)
        url = reverse('repository-list', args=[org.id, prod.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RepositoriesViewsSetCase(APITestCaseExpanded):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_a_new_repository(self):
        data = {
            'name': 'Test Repository',
            'description': 'Test Repository Description',
        }
        org = self.get_organization()
        product = self.get_product(org)
        url = reverse('repository-list', args=[org.id, product.id])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)

        data = response.json()

        self.assertEqual(data['name'], 'Test Repository')
        self.assertEqual(data['description'], 'Test Repository Description')

        qs = Repository.objects.filter(name='Test Repository')

        self.assertEqual(qs.exists(), True)
        self.assertEqual(qs.count(), 1)

        repository = qs.first()

        self.assertEqual(repository.name, 'Test Repository')
        self.assertEqual(repository.description, 'Test Repository Description')

        self.assertEqual(repository.product, product)
        self.assertEqual(repository.product.organization, org)

        url = reverse('repository-list', args=[org.id, product.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        repo = data['results'][0]

        self.assertEqual(data['count'], 1)
        self.assertEqual(repo['name'], 'Test Repository')
        self.assertEqual(repo['description'], 'Test Repository Description')

    @patch('organizations.serializers.requests.head')
    def test_create_a_new_repository_with_invalid_url(self, mock_head):
        mock_head.side_effect = ConnectionError

        data = {
            'name': 'Test Repository',
            'description': 'Test Repository Description',
            'url': 'http://invalidurl.com',
        }
        org = self.get_organization()
        product = self.get_product(org)
        url = reverse('repository-list', args=[org.id, product.id])

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        expected_error_message = "Unable to verify the repository's URL."
        self.assertIn(expected_error_message, response.data['url'][0])

    def test_create_repository_with_unsupported_scheme_url(self):
        data = {
            'name': 'Test Repository',
            'description': 'Test Repository Description',
            'url': 'ftp://invalidscheme.com',
        }
        org = self.get_organization()
        product = self.get_product(org)
        url = reverse('repository-list', args=[org.id, product.id])

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            'The URL must start with http or https.', response.data['url']
        )

    @patch('organizations.serializers.requests.head')
    def test_create_repository_with_inaccessible_url(self, mock_head):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        data = {
            'name': 'Test Repository',
            'description': 'Test Repository Description',
            'url': 'http://inaccessibleurl.com',
        }
        org = self.get_organization()
        product = self.get_product(org)
        url = reverse('repository-list', args=[org.id, product.id])

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "The repository's URL is not accessible.", response.data['url']
        )

    def test_if_existing_repositories_is_being_listed(self):
        org = self.get_organization()
        product = self.get_product(org)
        self.get_repository(product, name='Test Repository 2')
        self.get_repository(product, name='Test Repository 1')

        url = reverse('repository-list', args=[org.id, product.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['count'], 2)

        repo1 = data['results'][0]
        repo2 = data['results'][1]

        self.assertEqual(repo1['name'], 'Test Repository 1')
        self.assertEqual(repo1['description'], 'Test Repository Description')

        self.assertEqual(repo2['name'], 'Test Repository 2')
        self.assertEqual(repo2['description'], 'Test Repository Description')

    def test_if_only_product_repositories_is_beign_listed(self):
        org1 = self.get_organization()

        prod1 = self.get_product(
            org1,
            name='Test Product 1',
            description='Test Product Description 1',
        )

        prod2 = self.get_product(
            org1,
            name='Test Product 2',
            description='Test Product Description 2',
        )

        self.get_repository(prod1, name='Test Repository 1')
        self.get_repository(prod1, name='Test Repository 2')
        self.get_repository(prod2, name='Test Repository 3')

        url = reverse('repository-list', args=[org1.id, prod1.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['count'], 2)
        self.assertEqual(data['results'][0]['name'], 'Test Repository 2')
        self.assertEqual(data['results'][1]['name'], 'Test Repository 1')

    def test_update_a_existing_repository(self):
        org = self.get_organization()
        product = self.get_product(org)
        repository = self.get_repository(product)

        data = {
            'name': 'Test Repository Updated',
            'description': 'Test Repository Description Updated',
        }

        url = reverse(
            'repository-detail', args=[org.id, product.id, repository.id]
        )
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['name'], 'Test Repository Updated')
        self.assertEqual(
            data['description'], 'Test Repository Description Updated'
        )

        qs = Repository.objects.filter(name='Test Repository Updated')

        self.assertEqual(qs.exists(), True)
        self.assertEqual(qs.count(), 1)

        repository = qs.first()

        self.assertEqual(repository.name, 'Test Repository Updated')
        self.assertEqual(
            repository.description, 'Test Repository Description Updated'
        )

        self.assertEqual(repository.product, product)
        self.assertEqual(repository.product.organization, org)

        url = reverse(
            'repository-detail', args=[org.id, product.id, repository.id]
        )
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['name'], 'Test Repository Updated')
        self.assertEqual(
            data['description'], 'Test Repository Description Updated'
        )

    def test_delete_a_existing_repository(self):
        org = self.get_organization()
        product = self.get_product(org)
        repository = self.get_repository(product)

        url = reverse(
            'repository-detail', args=[org.id, product.id, repository.id]
        )
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, 204)

        qs = Repository.objects.filter(name='Test Repository')

        self.assertEqual(qs.exists(), False)
        self.assertEqual(qs.count(), 0)

        url = reverse(
            'repository-detail', args=[org.id, product.id, repository.id]
        )
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 404)

        url = reverse('repository-list', args=[org.id, product.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['count'], 0)

    def get_repository_urls(self, url_group):
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        url = reverse(
            'repository-detail',
            args=[self.org.id, self.product.id, self.repository.id],
        )
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        return data[url_group]

    def test_if_latest_metric_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('latest_values')
        metrics_url = latest_values_urls['metrics']
        response = self.client.get(metrics_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_latest_measures_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('latest_values')
        measures_url = latest_values_urls['measures']
        response = self.client.get(measures_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_latest_subcharacteristics_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('latest_values')
        subcharacteristics_url = latest_values_urls['subcharacteristics']
        response = self.client.get(subcharacteristics_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_latest_characteristics_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('latest_values')
        characteristics_url = latest_values_urls['characteristics']
        response = self.client.get(characteristics_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_latest_tsqmi_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('latest_values')
        tsqmi_url = latest_values_urls['tsqmi']
        response = self.client.get(tsqmi_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_historical_metrics_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('historical_values')
        metrics_url = latest_values_urls['metrics']
        response = self.client.get(metrics_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_historical_measures_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('historical_values')
        measures_url = latest_values_urls['measures']
        response = self.client.get(measures_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_historical_subcharacteristics_values_action_url_is_working(
        self,
    ):
        latest_values_urls = self.get_repository_urls('historical_values')
        subcharacteristics_url = latest_values_urls['subcharacteristics']
        response = self.client.get(subcharacteristics_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_historical_characteristics_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('historical_values')
        characteristics_url = latest_values_urls['characteristics']
        response = self.client.get(characteristics_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_historical_tsqmi_values_action_url_is_working(self):
        latest_values_urls = self.get_repository_urls('historical_values')
        tsqmi_url = latest_values_urls['tsqmi']
        response = self.client.get(tsqmi_url, format='json')
        self.assertEqual(response.status_code, 200)

    def test_if_calculate_math_model_is_working(self):
        actions_urls = self.get_repository_urls('actions')
        url = actions_urls['calculate-math-model']
        data = {
            "github": {
                "metrics": [
                    {"name": "total_issues", "value": 2},
                    {"name": "resolved_issues", "value": 1}
                ]
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)

    def test_if_is_not_allowed_to_create_repositories_with_same_name(self):
        data = {
            'name': 'Test Repository',
            'description': 'Test Repository Description',
        }
        org = self.get_organization()
        product = self.get_product(org)
        url = reverse('repository-list', args=[org.id, product.id])

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)
