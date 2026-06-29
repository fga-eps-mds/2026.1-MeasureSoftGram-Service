from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

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
