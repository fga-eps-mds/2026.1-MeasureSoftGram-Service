from unittest.mock import MagicMock, patch

import requests as requests_lib
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory

from rest_framework.request import Request as DRFRequest

from grafana_proxy.permissions import CanAccessDashboard, CanAccessProduct, HasRepositoryAccess
from grafana_proxy.serializers import GrafanaDashboardSerializer
from grafana_proxy.services import GrafanaAPIClient
from organizations.models import Repository
from utils.tests import APITestCaseExpanded

User = get_user_model()

DASHBOARD_UID = 'test-dashboard-uid'
GRAFANA_DASHBOARD_DATA = {
    'dashboard': {'title': 'Test Dashboard', 'uid': DASHBOARD_UID},
    'meta': {'description': 'Test description', 'slug': 'test-dashboard'},
}
GRAFANA_URL_PATH = f'/d/{DASHBOARD_UID}/test-dashboard?orgId=1&var-product=1&kiosk&theme=light'

LIST_URL = '/api/v1/grafana/dashboards/'


def dashboard_url(uid=DASHBOARD_UID):
    return f'/api/v1/grafana/dashboard/{uid}/'


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

class GrafanaUnauthenticatedTest(APITestCaseExpanded):
    def test_list_dashboards_requires_auth(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_dashboard_requires_auth(self):
        response = self.client.get(dashboard_url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# GET /api/v1/grafana/dashboards/
# ---------------------------------------------------------------------------

class GrafanaListDashboardsTest(APITestCaseExpanded):
    def setUp(self):
        self.client = APIClient()
        self.user = self.get_or_create_test_user()
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_returns_200_with_dashboards(self, MockClient):
        MockClient.return_value.get_dashboards.return_value = [
            {
                'uid': DASHBOARD_UID,
                'title': 'Test Dashboard',
                'tags': ['measuresoftgram'],
                'description': '',
            }
        ]
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['uid'], DASHBOARD_UID)
        self.assertEqual(data['results'][0]['title'], 'Test Dashboard')

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_returns_empty_list_when_grafana_has_no_dashboards(self, MockClient):
        MockClient.return_value.get_dashboards.return_value = []
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], 0)
        self.assertEqual(response.json()['results'], [])

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_has_repo_selector_true_only_for_hierarquia_qualidade(self, MockClient):
        MockClient.return_value.get_dashboards.return_value = [
            {'uid': 'hierarquia-qualidade', 'title': 'Evolução', 'tags': [], 'description': ''},
            {'uid': 'saude-qualidade-repo', 'title': 'Saúde', 'tags': [], 'description': ''},
            {'uid': 'outro-uid', 'title': 'Outro', 'tags': [], 'description': ''},
        ]
        response = self.client.get(LIST_URL)
        results = {r['uid']: r for r in response.json()['results']}
        self.assertTrue(results['hierarquia-qualidade']['has_repo_selector'])
        self.assertFalse(results['saude-qualidade-repo']['has_repo_selector'])
        self.assertFalse(results['outro-uid']['has_repo_selector'])

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_response_contains_expected_fields(self, MockClient):
        MockClient.return_value.get_dashboards.return_value = [
            {'uid': DASHBOARD_UID, 'title': 'T', 'tags': ['measuresoftgram'], 'description': 'D'},
        ]
        response = self.client.get(LIST_URL)
        result = response.json()['results'][0]
        for field in ('uid', 'title', 'description', 'tags', 'has_repo_selector'):
            self.assertIn(field, result, f'campo "{field}" ausente na resposta')


# ---------------------------------------------------------------------------
# GET /api/v1/grafana/dashboard/{uid}/
# ---------------------------------------------------------------------------

class GrafanaGetDashboardTest(APITestCaseExpanded):
    def setUp(self):
        self.client = APIClient()
        self.user = self.get_or_create_test_user()
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)

    # --- Parâmetros obrigatórios ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_missing_product_id_returns_400(self, MockClient):
        response = self.client.get(dashboard_url())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('product_id', response.json()['detail'])

    # --- Dashboard não encontrado ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_unknown_uid_returns_404(self, MockClient):
        MockClient.return_value.get_dashboard_by_uid.return_value = None
        response = self.client.get(
            dashboard_url('uid-inexistente'),
            {'product_id': self.product.id},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Controle de acesso ao produto ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_user_without_product_access_returns_403(self, MockClient):
        MockClient.return_value.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        other_user = User.objects.create(username='intruder', email='intruder@test.com')
        self.client.force_authenticate(other_user)
        response = self.client.get(dashboard_url(), {'product_id': self.product.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_product_from_other_org_returns_403(self, MockClient):
        MockClient.return_value.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        other_org = self.get_organization(name='Other Org', add_user=False)
        other_product = self.get_product(other_org, name='Other Product')
        response = self.client.get(dashboard_url(), {'product_id': other_product.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Requisição válida sem repositório ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_valid_request_without_repository_returns_200(self, MockClient):
        mock = MockClient.return_value
        mock.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        mock.build_dashboard_url.return_value = GRAFANA_URL_PATH
        response = self.client.get(dashboard_url(), {'product_id': self.product.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['dashboard_uid'], DASHBOARD_UID)
        self.assertEqual(data['title'], 'Test Dashboard')
        self.assertEqual(data['product_id'], self.product.id)
        self.assertIsNone(data['repository'])
        self.assertIn('grafana_url', data)

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_grafana_url_contains_url_path(self, MockClient):
        mock = MockClient.return_value
        mock.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        mock.build_dashboard_url.return_value = GRAFANA_URL_PATH
        response = self.client.get(dashboard_url(), {'product_id': self.product.id})
        grafana_url = response.json()['grafana_url']
        self.assertIn(GRAFANA_URL_PATH, grafana_url)
        self.assertTrue(grafana_url.startswith('http'))

    # --- Requisição válida com repositório ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_valid_request_with_repository_returns_200(self, MockClient):
        mock = MockClient.return_value
        mock.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        mock.build_dashboard_url.return_value = GRAFANA_URL_PATH
        response = self.client.get(dashboard_url(), {
            'product_id': self.product.id,
            'repository_id': self.repository.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsNotNone(data['repository'])
        self.assertEqual(data['repository']['id'], self.repository.id)
        self.assertEqual(data['repository']['name'], self.repository.name)

    # --- Repositório não pertence ao produto ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_repository_from_different_product_returns_400(self, MockClient):
        mock = MockClient.return_value
        mock.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        mock.build_dashboard_url.return_value = GRAFANA_URL_PATH
        # Segundo produto na mesma org — usuário tem acesso ao repo,
        # mas o repo não pertence ao product_id informado
        other_product = self.get_product(self.org, name='Other Product')
        other_repo = self.get_repository(other_product, name='Other Repository')
        response = self.client.get(dashboard_url(), {
            'product_id': self.product.id,
            'repository_id': other_repo.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Controle de acesso ao repositório ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_user_without_repository_access_returns_403(self, MockClient):
        MockClient.return_value.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        # Usuário sem vínculo com a org não tem acesso ao repositório
        intruder = User.objects.create(username='intruder2', email='intruder2@test.com')
        intruder_client = APIClient()
        intruder_client.force_authenticate(intruder)
        response = intruder_client.get(dashboard_url(), {
            'product_id': self.product.id,
            'repository_id': self.repository.id,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- build_dashboard_url é chamado com parâmetros corretos ---

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_build_dashboard_url_called_with_product_and_repository(self, MockClient):
        mock = MockClient.return_value
        mock.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        mock.build_dashboard_url.return_value = GRAFANA_URL_PATH
        self.client.get(dashboard_url(), {
            'product_id': self.product.id,
            'repository_id': self.repository.id,
        })
        mock.build_dashboard_url.assert_called_once_with(
            uid=DASHBOARD_UID,
            product_id=self.product.id,
            repository_id=self.repository.id,
        )

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_build_dashboard_url_called_without_repository_when_not_provided(self, MockClient):
        mock = MockClient.return_value
        mock.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        mock.build_dashboard_url.return_value = GRAFANA_URL_PATH
        self.client.get(dashboard_url(), {'product_id': self.product.id})
        mock.build_dashboard_url.assert_called_once_with(
            uid=DASHBOARD_UID,
            product_id=self.product.id,
            repository_id=None,
        )

    @patch('grafana_proxy.views.GrafanaAPIClient')
    def test_repo_from_different_org_returns_403_on_dashboard_access(self, MockClient):
        """Cobre views.py:80 — CanAccessDashboard falha quando repo é de outra org."""
        MockClient.return_value.get_dashboard_by_uid.return_value = GRAFANA_DASHBOARD_DATA
        other_org = self.get_organization(name='Other Org', add_user=False)
        other_product = self.get_product(other_org, name='Other Product')
        other_repo = self.get_repository(other_product, name='Other Repo')
        response = self.client.get(dashboard_url(), {
            'product_id': self.product.id,
            'repository_id': other_repo.id,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class HasRepositoryAccessPermissionTest(APITestCaseExpanded):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = self.get_or_create_test_user()
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        self.permission = HasRepositoryAccess()

    def _make_request(self, user=None):
        request = self.factory.get('/')
        request.user = user or self.user
        return request

    def test_has_permission_returns_true_for_authenticated_user(self):
        request = self._make_request()
        self.assertTrue(self.permission.has_permission(request, None))

    def test_has_permission_returns_false_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        request = self._make_request(user=AnonymousUser())
        self.assertFalse(self.permission.has_permission(request, None))

    def test_has_object_permission_returns_true_for_own_repository(self):
        request = self._make_request()
        self.assertTrue(self.permission.has_object_permission(request, None, self.repository))

    def test_has_object_permission_returns_false_for_non_repository_object(self):
        request = self._make_request()
        self.assertFalse(self.permission.has_object_permission(request, None, object()))

    def test_has_object_permission_returns_false_for_other_org_repo(self):
        other_org = self.get_organization(name='Other Org', add_user=False)
        other_product = self.get_product(other_org, name='Other Product')
        other_repo = self.get_repository(other_product, name='Other Repo')
        request = self._make_request()
        self.assertFalse(self.permission.has_object_permission(request, None, other_repo))

    def test_can_access_repository_returns_true_for_superuser(self):
        self.user.is_superuser = True
        self.user.save()
        self.assertTrue(self.permission._user_can_access_repository(self.user, self.repository))

    def test_can_access_repository_returns_false_for_unrelated_user(self):
        unrelated = get_user_model().objects.create(username='unrelated', email='unrelated@test.com')
        self.assertFalse(self.permission._user_can_access_repository(unrelated, self.repository))


class CanAccessProductPermissionTest(APITestCaseExpanded):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = self.get_or_create_test_user()
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.permission = CanAccessProduct()

    def _make_request(self, user=None, params=None):
        raw = self.factory.get('/', params or {})
        request = DRFRequest(raw)
        request.user = user or self.user
        return request

    def test_unauthenticated_returns_false(self):
        from django.contrib.auth.models import AnonymousUser
        request = self._make_request(user=AnonymousUser())
        self.assertFalse(self.permission.has_permission(request, None))

    def test_superuser_returns_true_without_product_id(self):
        self.user.is_superuser = True
        self.user.save()
        request = self._make_request()
        self.assertTrue(self.permission.has_permission(request, None))

    def test_missing_product_id_returns_false(self):
        request = self._make_request(params={})
        self.assertFalse(self.permission.has_permission(request, None))

    def test_valid_product_id_owned_by_user_returns_true(self):
        request = self._make_request(params={'product_id': self.product.id})
        self.assertTrue(self.permission.has_permission(request, None))

    def test_product_from_other_org_returns_false(self):
        other_org = self.get_organization(name='Other Org', add_user=False)
        other_product = self.get_product(other_org, name='Other Product')
        request = self._make_request(params={'product_id': other_product.id})
        self.assertFalse(self.permission.has_permission(request, None))

    def test_invalid_product_id_returns_false(self):
        request = self._make_request(params={'product_id': 'not-a-number'})
        self.assertFalse(self.permission.has_permission(request, None))


class CanAccessDashboardPermissionTest(APITestCaseExpanded):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = self.get_or_create_test_user()
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)
        self.permission = CanAccessDashboard()

    def _make_request(self, user=None, params=None):
        raw = self.factory.get('/', params or {})
        request = DRFRequest(raw)
        request.user = user or self.user
        return request

    def test_unauthenticated_returns_false(self):
        from django.contrib.auth.models import AnonymousUser
        request = self._make_request(user=AnonymousUser())
        self.assertFalse(self.permission.has_permission(request, None))

    def test_no_repository_id_returns_true(self):
        request = self._make_request(params={})
        self.assertTrue(self.permission.has_permission(request, None))

    def test_own_repository_id_returns_true(self):
        request = self._make_request(params={'repository_id': self.repository.id})
        self.assertTrue(self.permission.has_permission(request, None))

    def test_other_org_repository_returns_false(self):
        other_org = self.get_organization(name='Other Org', add_user=False)
        other_product = self.get_product(other_org, name='Other Product')
        other_repo = self.get_repository(other_product, name='Other Repo')
        request = self._make_request(params={'repository_id': other_repo.id})
        self.assertFalse(self.permission.has_permission(request, None))

    def test_nonexistent_repository_id_returns_false(self):
        request = self._make_request(params={'repository_id': 999999})
        self.assertFalse(self.permission.has_permission(request, None))

    def test_invalid_repository_id_returns_false(self):
        request = self._make_request(params={'repository_id': 'abc'})
        self.assertFalse(self.permission.has_permission(request, None))


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

class GrafanaAPIClientGetDashboardsTest(TestCase):
    def setUp(self):
        with patch('grafana_proxy.services.settings') as mock_settings:
            mock_settings.GRAFANA_CONFIG = {
                'BASE_URL': 'http://grafana:3000',
                'USERNAME': 'admin',
                'PASSWORD': 'admin',
                'TIMEOUT': 5,
            }
            self.client_api = GrafanaAPIClient()

    @patch('grafana_proxy.services.requests.get')
    def test_get_dashboards_returns_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = [{'uid': 'abc', 'title': 'Test'}]
        mock_get.return_value = mock_response
        result = self.client_api.get_dashboards()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['uid'], 'abc')

    @patch('grafana_proxy.services.requests.get')
    def test_get_dashboards_returns_empty_list_on_error(self, mock_get):
        mock_get.side_effect = requests_lib.RequestException('connection error')
        result = self.client_api.get_dashboards()
        self.assertEqual(result, [])


class GrafanaAPIClientGetDashboardByUidTest(TestCase):
    def setUp(self):
        with patch('grafana_proxy.services.settings') as mock_settings:
            mock_settings.GRAFANA_CONFIG = {
                'BASE_URL': 'http://grafana:3000',
                'USERNAME': 'admin',
                'PASSWORD': 'admin',
                'TIMEOUT': 5,
            }
            self.client_api = GrafanaAPIClient()

    @patch('grafana_proxy.services.requests.get')
    def test_returns_dashboard_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'dashboard': {'uid': 'xyz'}, 'meta': {'slug': 'test'}}
        mock_get.return_value = mock_response
        result = self.client_api.get_dashboard_by_uid('xyz')
        self.assertIsNotNone(result)
        self.assertEqual(result['meta']['slug'], 'test')

    @patch('grafana_proxy.services.requests.get')
    def test_returns_none_on_404(self, mock_get):
        mock_response = MagicMock()
        http_error = requests_lib.HTTPError(response=MagicMock(status_code=404))
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        result = self.client_api.get_dashboard_by_uid('nonexistent')
        self.assertIsNone(result)

    @patch('grafana_proxy.services.requests.get')
    def test_returns_none_on_request_exception(self, mock_get):
        mock_get.side_effect = requests_lib.RequestException('timeout')
        result = self.client_api.get_dashboard_by_uid('xyz')
        self.assertIsNone(result)

    @patch('grafana_proxy.services.requests.get')
    def test_returns_none_on_non_404_http_error(self, mock_get):
        mock_response = MagicMock()
        http_error = requests_lib.HTTPError(response=MagicMock(status_code=500))
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        result = self.client_api.get_dashboard_by_uid('xyz')
        self.assertIsNone(result)


class GrafanaAPIClientBuildDashboardUrlTest(TestCase):
    def setUp(self):
        with patch('grafana_proxy.services.settings') as mock_settings:
            mock_settings.GRAFANA_CONFIG = {
                'BASE_URL': 'http://grafana:3000',
                'USERNAME': 'admin',
                'PASSWORD': 'admin',
                'TIMEOUT': 5,
            }
            self.client_api = GrafanaAPIClient()

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_contains_uid_and_slug(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'my-dash'}}
        url = self.client_api.build_dashboard_url(uid='my-uid')
        self.assertIn('/d/my-uid/my-dash', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_fallback_slug_when_dashboard_not_found(self, mock_get):
        mock_get.return_value = None
        url = self.client_api.build_dashboard_url(uid='my-uid')
        self.assertIn('/d/my-uid/my-uid', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_with_product_id(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'dash'}}
        url = self.client_api.build_dashboard_url(uid='uid', product_id=5)
        self.assertIn('var-product=5', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_with_repository_id(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'dash'}}
        url = self.client_api.build_dashboard_url(uid='uid', repository_id=3)
        self.assertIn('var-repository=3', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_without_repository_omits_var(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'dash'}}
        url = self.client_api.build_dashboard_url(uid='uid', product_id=1)
        self.assertNotIn('var-repository', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_kiosk_mode_enabled(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'dash'}}
        url = self.client_api.build_dashboard_url(uid='uid', kiosk=True)
        self.assertIn('&kiosk', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_kiosk_mode_disabled(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'dash'}}
        url = self.client_api.build_dashboard_url(uid='uid', kiosk=False)
        self.assertNotIn('&kiosk', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_theme_light(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'dash'}}
        url = self.client_api.build_dashboard_url(uid='uid', theme='light')
        self.assertIn('theme=light', url)

    @patch.object(GrafanaAPIClient, 'get_dashboard_by_uid')
    def test_build_url_with_organization_id(self, mock_get):
        mock_get.return_value = {'meta': {'slug': 'dash'}}
        url = self.client_api.build_dashboard_url(uid='uid', organization_id=7)
        self.assertIn('var-organization=7', url)


class GrafanaAPIClientProxyDashboardTest(TestCase):
    def setUp(self):
        with patch('grafana_proxy.services.settings') as mock_settings:
            mock_settings.GRAFANA_CONFIG = {
                'BASE_URL': 'http://grafana:3000',
                'USERNAME': 'admin',
                'PASSWORD': 'admin',
                'TIMEOUT': 5,
            }
            self.client_api = GrafanaAPIClient()

    @patch('grafana_proxy.services.requests.get')
    def test_proxy_returns_response(self, mock_get):
        mock_response = MagicMock()
        mock_get.return_value = mock_response
        result = self.client_api.proxy_dashboard('/d/uid/slug')
        self.assertIsNotNone(result)

    @patch('grafana_proxy.services.requests.get')
    def test_proxy_returns_none_on_error(self, mock_get):
        mock_get.side_effect = requests_lib.RequestException('timeout')
        result = self.client_api.proxy_dashboard('/d/uid/slug')
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class GrafanaDashboardSerializerTest(APITestCaseExpanded):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.repository = self.get_repository(self.product)

    def _make_data(self, repository_id=None):
        return {
            'dashboard_uid': 'test-uid',
            'title': 'Test',
            'grafana_url': 'http://localhost:5000/d/test-uid/test',
            'product_id': self.product.id,
            'repository_id': repository_id,
        }

    def test_get_repository_returns_none_when_no_id(self):
        s = GrafanaDashboardSerializer(self._make_data())
        self.assertIsNone(s.data['repository'])

    def test_get_repository_returns_dict_when_repo_exists(self):
        s = GrafanaDashboardSerializer(self._make_data(repository_id=self.repository.id))
        self.assertIsNotNone(s.data['repository'])
        self.assertEqual(s.data['repository']['id'], self.repository.id)
        self.assertEqual(s.data['repository']['name'], self.repository.name)

    def test_get_repository_returns_none_when_repo_does_not_exist(self):
        s = GrafanaDashboardSerializer(self._make_data(repository_id=999999))
        self.assertIsNone(s.data['repository'])
