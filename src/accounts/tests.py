from unittest.mock import MagicMock, patch

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from parameterized import parameterized
from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse

from utils.tests import APITestCaseExpanded

User = get_user_model()


class AccountsViews(APITestCaseExpanded):
    @property
    def _data_signin(self):
        return {
            'username': 'Test-User',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test_user@email.com',
            'password': 'testpass',
        }

    def setUp(self):
        self.user = User.objects.create(
            username='test-user',
            first_name='test',
            last_name='user',
            email='test_user@email.com',
        )
        self.password = 'testpass'
        self.user.set_password(self.password)
        self.user.save()

    def test_logout_acccount(self):
        token = Token.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user, token=token)

        url = reverse('accounts-logout')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Token.objects.count(), 1)

    def test_fail_logout_without_authentication(self):
        url = reverse('accounts-logout')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 401)

    def test_create_new_account(self):
        url = reverse('accounts-signin')
        User.objects.all().delete()
        response = self.client.post(url, data=self._data_signin, format='json')
        self.assertEqual(response.status_code, 201, response.json())

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            Token.objects.filter(user=User.objects.first()).count(), 1
        )
        self.assertEqual(Token.objects.first().key, response.json()['key'])

    @parameterized.expand(
        [('username', 'username'), ('email', 'email address')]
    )
    def test_fail_create_account_already_exists(self, field, error):
        url = reverse('accounts-signin')
        data = self._data_signin
        data[field] = getattr(self.user, field)

        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            f'A user with that {error} already exists.', response.json()[field]
        )

    @parameterized.expand([('username',), ('email',)])
    def test_login_accounts(self, field):
        url = reverse('accounts-login')
        response = self.client.post(
            url,
            data={field: getattr(self.user, field), 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(
            Token.objects.get(user=self.user).key, response.json()['key']
        )

    def test_fail_login_username_and_email(self):
        url = reverse('accounts-login')
        response = self.client.post(
            url,
            data={
                'username': self.user.username,
                'email': self.user.email,
                'password': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.json())
        self.assertIn(
            'ONLY Username OR email.', response.json()['non_field_errors']
        )

    def test_fail_login_nor_username_nor_email(self):
        url = reverse('accounts-login')
        response = self.client.post(
            url, data={'password': self.password}, format='json'
        )

        self.assertEqual(response.status_code, 400, response.json())
        self.assertIn(
            'Username OR email required.', response.json()['non_field_errors']
        )

    @parameterized.expand(
        [('username', 'invalid'), ('email', 'invalid@email.com')]
    )
    def test_fail_login_nonexistent_user(self, field, value):
        url = reverse('accounts-login')
        response = self.client.post(
            url, data={field: value, 'password': self.password}, format='json'
        )

        self.assertEqual(response.status_code, 400, response.json())
        self.assertIn(
            'Username or email nonexistent.',
            response.json()['non_field_errors'],
        )

    def test_fail_login_wrong_password(self):
        url = reverse('accounts-login')
        response = self.client.post(
            url,
            data={'username': self.user.username, 'password': 'wrongpass'},
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.json())
        self.assertIn(
            'Invalid username/email or password',
            response.json()['non_field_errors'],
        )

    def test_retrieve_account(self):
        url = reverse('accounts-retrieve')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token '
            + Token.objects.create(user=self.user).key
        )
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 200, response.json())
        fields = ('username', 'first_name', 'last_name', 'email')
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(
                    getattr(self.user, field), response.json()[field]
                )

    def test_retrieve_accounts_via_github(self):
        url = reverse('accounts-retrieve')

        extra_data = {
            'avatar_url': 'https://avatars.githubusercontent.com/u/teste?v=4',
            'organizations_url': 'https://api.github.com/users/test/orgs',
            'repos_url': 'https://api.github.com/users/test/repos',
        }

        socialaccount = SocialAccount.objects.create(
            user=self.user, extra_data=extra_data
        )

        self.client.credentials(
            HTTP_AUTHORIZATION='Token '
            + Token.objects.create(user=self.user).key
        )
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 200, response.json())
        fields = ('avatar_url', 'repos_url', 'organizations_url')
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(
                    socialaccount.extra_data[field], response.json()[field]
                )

    def test_fail_retrieve_account_anonymous(self):
        url = reverse('accounts-retrieve')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 401, response.json())
        self.assertIn(
            'Authentication credentials were not provided.',
            response.json()['detail'],
        )

    def test_access_token(self):
        url = reverse('api-token-retrieve')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token '
            + Token.objects.create(user=self.user).key
        )
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(
            Token.objects.get(user=self.user).key, response.json()['key']
        )

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_user_repos_success(self, mock_post, mock_get):
        repos = [{'id': 1, 'name': 'repo1'}, {'id': 2, 'name': 'repo2'}]

        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {'access_token': 'gh_token_123'}
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = repos
        mock_get.return_value = mock_get_response

        self.client.credentials(
            HTTP_AUTHORIZATION='Token '
            + Token.objects.create(user=self.user).key
        )
        url = reverse('user-repos')
        response = self.client.get(url, {'code': 'valid_code'}, format='json')

        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()['total_count'], 2)
        self.assertEqual(response.json()['items'], repos)

    @patch('accounts.views.requests.post')
    def test_user_repos_github_auth_failure(self, mock_post):
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {'error': 'bad_verification_code'}
        mock_post.return_value = mock_post_response

        self.client.credentials(
            HTTP_AUTHORIZATION='Token '
            + Token.objects.create(user=self.user).key
        )
        url = reverse('user-repos')
        response = self.client.get(url, {'code': 'bad_code'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'Falha na autenticação do GitHub')

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_user_repos_non_list_response(self, mock_post, mock_get):
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {'access_token': 'gh_token_123'}
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {'message': 'Not Found'}
        mock_get.return_value = mock_get_response

        self.client.credentials(
            HTTP_AUTHORIZATION='Token '
            + Token.objects.create(user=self.user).key
        )
        url = reverse('user-repos')
        response = self.client.get(url, {'code': 'valid_code'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_count'], 0)
        self.assertEqual(response.json()['items'], [])

    def test_user_repos_unauthenticated(self):
        url = reverse('user-repos')
        response = self.client.get(url, {'code': 'any_code'}, format='json')
        self.assertEqual(response.status_code, 401)

    @patch('accounts.views.requests.get')
    def test_github_organizations_success(self, mock_get):
        self.user.github_access_token = 'gh_token_123'
        self.user.save()

        def side_effect(url, headers=None):
            resp = MagicMock()
            resp.status_code = 200
            if "api.github.com/user/orgs" in url:
                resp.json.return_value = [
                    {'id': 456, 'login': 'org2', 'avatar_url': 'http://avatar2', 'description': 'desc2'}
                ]
            else:
                resp.json.return_value = {
                    'id': 123, 'login': 'test-user', 'avatar_url': 'http://avatar1', 'bio': 'desc1'
                }
            return resp

        mock_get.side_effect = side_effect

        self.client.credentials(
            HTTP_AUTHORIZATION='Token '
            + Token.objects.create(user=self.user).key
        )
        url = reverse('github-organizations')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]['github_org_name'], 'test-user')
        self.assertEqual(response.json()[1]['github_org_name'], 'org2')

    @patch('accounts.views.requests.post')
    def test_github_validate_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404  # Credenciais válidas, token dummy não encontrado
        mock_post.return_value = mock_response

        url = reverse('github-validate')
        with patch('django.conf.settings.GITHUB_CLIENT_ID', 'test_client_id'), \
             patch('django.conf.settings.GITHUB_SECRET', 'test_secret'):
            response = self.client.post(url, {'client_id': 'test_client_id'}, format='json')
            
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['valid'])

    @patch('accounts.views.requests.post')
    def test_github_validate_bad_credentials(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401  # Bad credentials
        mock_post.return_value = mock_response

        url = reverse('github-validate')
        with patch('django.conf.settings.GITHUB_CLIENT_ID', 'test_client_id'), \
             patch('django.conf.settings.GITHUB_SECRET', 'test_secret'):
            response = self.client.post(url, {'client_id': 'test_client_id'}, format='json')
            
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['valid'])
        self.assertEqual(response.json()['reason'], 'Invalid GitHub Client ID or Client Secret')

    def test_github_validate_mismatch(self):
        url = reverse('github-validate')
        with patch('django.conf.settings.GITHUB_CLIENT_ID', 'backend_client_id'), \
             patch('django.conf.settings.GITHUB_SECRET', 'test_secret'):
            response = self.client.post(url, {'client_id': 'frontend_client_id'}, format='json')
            
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['valid'])
        self.assertEqual(response.json()['reason'], 'Client ID mismatch between frontend and backend')

    def test_github_validate_not_configured(self):
        url = reverse('github-validate')
        with patch('django.conf.settings.GITHUB_CLIENT_ID', ''), \
             patch('django.conf.settings.GITHUB_SECRET', ''):
            response = self.client.post(url, {'client_id': 'any_id'}, format='json')
            
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['valid'])
        self.assertEqual(response.json()['reason'], 'Backend GitHub credentials are not configured')

