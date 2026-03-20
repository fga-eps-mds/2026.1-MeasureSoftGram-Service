from rest_framework.authtoken.models import Token
from rest_framework.mixins import status
from rest_framework.test import APIClient
from rest_framework.viewsets import reverse

from release_configuration.models import ReleaseConfiguration
from utils.tests import APITestCaseExpanded

# Create your tests here.


def _get_product_detail(*args):
    return reverse('product-detail', args=args)


class TestUnauthenticatedConfigEndpoints(APITestCaseExpanded):
    def setUp(self):
        self.request = APIClient()
        self.org = self.get_organization()
        self.prod = self.get_product(self.org)

    def test_that_unauthorized_is_prohibited(self):
        response = self.request.get(
            _get_product_detail(self.org.id, self.prod.id)
        )
        self.assertIsNotNone(self.org.id)
        self.assertIsNotNone(self.prod.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestConfigEnpoints(APITestCaseExpanded):
    def setUp(self):
        self.request = APIClient()
        self.user = self.get_or_create_test_user()
        self.token = Token.objects.create(user=self.user)
        self.request.force_authenticate(user=self.user, token=self.token)
        self.org = self.get_organization()
        self.prod = self.get_product(self.org)

    def test_user_not_created_configs(self):
        detail_items = self.request.get(
            _get_product_detail(self.org.id, self.prod.id)
        )
        pre_config_uri = detail_items.json()['actions']
        self.assertIsNotNone(pre_config_uri)

        configs_resp = self.request.get(
            pre_config_uri['get current release-config']
        )

        self.assertEqual(configs_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(configs_resp.json()['created_config'])

    def test_user_created_configs(self):
        detail_items = self.request.get(
            _get_product_detail(self.org.id, self.prod.id)
        )
        pre_config_uri = detail_items.json()['actions']

        measures = [
            {
                'key': 'passed_tests',
                'weight': 100,
                'min_threshold': 0,
                'max_threshold': 1,
            }
        ]
        subcharacteristics = [
            {'key': 'testing_status', 'weight': 100, 'measures': measures}
        ]
        characteristics = [
            {
                'key': 'reliability',
                'weight': 100,
                'subcharacteristics': subcharacteristics,
            }
        ]

        data = {
            'name': 'Test release-config',
            'data': {'characteristics': characteristics},
        }
        response = self.request.post(
            pre_config_uri['create a new release-config'], data, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        configs_resp = self.request.get(
            pre_config_uri['get current release-config']
        )
        print(configs_resp.json())

        self.assertIn(
            dict(
                filter(
                    lambda item_tuple: item_tuple[0] == 'id',
                    configs_resp.json().items(),
                )
            ),
            ReleaseConfiguration.objects.values('id').filter(
                id=configs_resp.json()['id']
            ),
        )
        self.assertEqual(configs_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(configs_resp.json()['created_config'])
