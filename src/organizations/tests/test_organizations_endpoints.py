from rest_framework.authtoken.models import Token
from rest_framework.exceptions import status
from rest_framework.test import APIClient

from organizations.models import Organization
from utils.tests import APITestCaseExpanded
from django.contrib.auth import get_user_model
from django.urls import reverse


class PublicOrganizationsViewsTestCase(APITestCaseExpanded):
    def test_unauthenticated_not_allowed(self):
        org = self.get_organization()
        url = reverse('organization-detail', args=[org.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)


class OrganizationsViewsTestCase(APITestCaseExpanded):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test-user', password='test-pass'
        )

        self.client = APIClient()
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )

    def test_create_a_new_organization(self):
        url = reverse('organization-list')
        data = {
            'name': 'Test Organization',
            'description': 'Test Organization Description',
            'key': 'test-organization-key',
        }
        response = self.client.post(url, data, format='json')
        print(response.content)
        self.assertEqual(response.status_code, 201)

        data = response.json()

        self.assertEqual(data['name'], 'Test Organization')
        self.assertEqual(data['description'], 'Test Organization Description')

        organization_created = Organization.objects.get(
            name='Test Organization'
        )
        self.assertEqual(organization_created.admin, self.user)

        qs = Organization.objects.filter(name='Test Organization')

        self.assertEqual(qs.exists(), True)
        self.assertEqual(qs.count(), 1)

        organization_created = qs.first()

        self.assertEqual(organization_created.admin, self.user)

    def compare_organization_data(self, data, org):
        self.assertEqual(data['id'], org.id)
        self.assertEqual(data['name'], org.name)
        self.assertEqual(data['description'], org.description)

    def test_if_existing_organization_is_being_listed(self):
        org = self.get_organization()
        url = reverse('organization-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()['results']
        self.compare_organization_data(data[0], org)

    def test_update_a_existing_organization(self):
        org: Organization = self.get_organization()
        url = reverse('organization-detail', args=[org.id])
        data = {
            'name': 'Test Organization Updated',
            'description': 'Test Organization Description Updated',
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        org = Organization.objects.get(id=org.id)
        self.compare_organization_data(data, org)

    def test_patch_update_a_existing_organization(self):
        org: Organization = self.get_organization()
        url = reverse('organization-detail', args=[org.id])
        data = {
            'description': 'Test Organization Description Updated',
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        org = Organization.objects.get(id=org.id)
        self.compare_organization_data(data, org)

    def test_delete_a_existing_organization(self):
        org: Organization = self.get_organization()
        url = reverse('organization-detail', args=[org.id])
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, 204)
        qs = Organization.objects.filter(id=org.id).exists()
        self.assertEqual(qs, False)

    def test_list_all_existing_organizations(self):
        self.get_organization(name='Test Organization 1')
        self.get_organization(name='Test Organization 2')
        self.get_organization(name='Test Organization 3')

        url = reverse('organization-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['count'], 3)
        self.assertEqual(data['next'], None)
        self.assertEqual(data['previous'], None)
        self.assertEqual(data['results'][0]['name'], 'Test Organization 1')
        self.assertEqual(data['results'][1]['name'], 'Test Organization 2')
        self.assertEqual(data['results'][2]['name'], 'Test Organization 3')

    def test_if_an_organizations_product_urls_list_is_returned(self):
        org: Organization = self.get_organization()
        self.get_product(org)

        url = reverse('organization-detail', args=[org.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIsInstance(data['products'], list)
        self.assertEqual(len(data['products']), 1)

        product_url = data['products'][0]

        self.assertIsInstance(product_url, str)

        response = self.client.get(product_url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['name'], 'Test Product')
        self.assertEqual(data['description'], 'Test Product Description')

    def test_if_create_product_action_url_is_working(self):
        org: Organization = self.get_organization()
        self.get_product(org)

        url = reverse('organization-detail', args=[org.id])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        actions = data['actions']
        create_new_product_url = actions['create a new product']

        self.assertIsInstance(create_new_product_url, str)

        data = {
            'name': 'Test Product 2',
            'description': 'Test Product Description 2',
        }

        response = self.client.post(
            create_new_product_url, data, format='json'
        )

        self.assertEqual(response.status_code, 201)

        data = response.json()

        self.assertEqual(data['name'], 'Test Product 2')
        self.assertEqual(data['description'], 'Test Product Description 2')

    def test_if_is_not_allowed_to_create_organizations_with_same_name(self):
        url = reverse('organization-list')

        data = {
            'name': 'Test Organization',
            'description': 'Test Organization Description',
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)


class OrganizationPermissionIsolationTestCase(APITestCaseExpanded):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test-user-1', password='test-pass-1'
        )
        self.other_user = get_user_model().objects.create_user(
            username='test-user-2', password='test-pass-2'
        )

        self.client = APIClient()
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )

    def test_user_cannot_see_other_users_organization(self):
        org = self.get_organization(name='Other Org', add_user=False)
        org.members.add(self.other_user)
        org.admin = self.other_user
        org.save()

        url = reverse('organization-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 0)

        detail_url = reverse('organization-detail', args=[org.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_see_other_users_product(self):
        org = self.get_organization(name='Other Org', add_user=False)
        org.members.add(self.other_user)
        org.admin = self.other_user
        org.save()
        product = self.get_product(org, name='Other Product')

        url = reverse('product-list', kwargs={'organization_pk': org.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        detail_url = reverse('product-detail', kwargs={'organization_pk': org.id, 'pk': product.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_see_other_users_repository(self):
        org = self.get_organization(name='Other Org', add_user=False)
        org.members.add(self.other_user)
        org.admin = self.other_user
        org.save()
        product = self.get_product(org, name='Other Product')
        repo = self.get_repository(product, name='Other Repo')

        url = reverse('repository-list', kwargs={'organization_pk': org.id, 'product_pk': product.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        detail_url = reverse('repository-detail', kwargs={'organization_pk': org.id, 'product_pk': product.id, 'pk': repo.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 404)


from unittest.mock import patch, MagicMock

class ImportOrganizationViewsTestCase(APITestCaseExpanded):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test-user', password='test-pass'
        )
        self.client = APIClient()
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )

    def test_import_org_no_name(self):
        url = reverse('organizations-import-list')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'github_org_name is required.')

    def test_import_org_no_token(self):
        url = reverse('organizations-import-list')
        self.user.github_access_token = None
        self.user.save()
        response = self.client.post(url, {'github_org_name': 'some-org'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'GitHub account not linked.')

    @patch('organizations.views.requests.get')
    def test_import_org_fetch_fail(self, mock_get):
        url = reverse('organizations-import-list')
        self.user.github_access_token = 'my-token'
        self.user.save()

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {'message': 'Not Found'}
        mock_get.return_value = mock_resp

        response = self.client.post(url, {'github_org_name': 'some-org'}, format='json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'Failed to fetch metadata from GitHub')

    @patch('organizations.views.requests.get')
    def test_import_org_personal_success(self, mock_get):
        url = reverse('organizations-import-list')
        self.user.github_access_token = 'my-token'
        self.user.save()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'id': 9999,
            'name': 'My Personal Org',
            'login': 'test-user',
            'avatar_url': 'http://avatar',
            'bio': 'My bio'
        }
        mock_get.return_value = mock_resp

        response = self.client.post(url, {'github_org_name': 'test-user'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['name'], 'My Personal Org')
        
        org = Organization.objects.get(github_org_id=9999)
        self.assertEqual(org.github_org_name, 'test-user')
        self.assertEqual(org.description, 'My bio')

    @patch('organizations.views.requests.get')
    def test_import_org_non_personal_success(self, mock_get):
        url = reverse('organizations-import-list')
        self.user.github_access_token = 'my-token'
        self.user.save()

        def side_effect(url, headers=None):
            resp = MagicMock()
            resp.status_code = 200
            if "api.github.com/user/memberships/orgs" in url:
                resp.json.return_value = {'state': 'active'}
            else:
                resp.json.return_value = {
                    'id': 8888,
                    'name': 'My Company Org',
                    'login': 'company-org',
                    'avatar_url': 'http://avatar-company',
                    'description': 'Our description'
                }
            return resp

        mock_get.side_effect = side_effect

        response = self.client.post(url, {'github_org_name': 'company-org'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['name'], 'My Company Org')
        
        org = Organization.objects.get(github_org_id=8888)
        self.assertEqual(org.github_org_name, 'company-org')
        self.assertEqual(org.description, 'Our description')

    @patch('organizations.views.requests.get')
    def test_import_org_non_personal_forbidden(self, mock_get):
        url = reverse('organizations-import-list')
        self.user.github_access_token = 'my-token'
        self.user.save()

        def side_effect(url, headers=None):
            resp = MagicMock()
            if "api.github.com/user/memberships/orgs" in url:
                resp.status_code = 403
                resp.json.return_value = {'message': 'Not a member'}
            else:
                resp.status_code = 200
                resp.json.return_value = {
                    'id': 8888,
                    'name': 'My Company Org',
                    'login': 'company-org',
                    'avatar_url': 'http://avatar-company',
                    'description': 'Our description'
                }
            return resp

        mock_get.side_effect = side_effect

        response = self.client.post(url, {'github_org_name': 'company-org'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], "User is not a member of organization 'company-org' in GitHub.")

    @patch('organizations.views.requests.get')
    def test_import_org_via_social_token(self, mock_get):
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        url = reverse('organizations-import-list')
        self.user.github_access_token = None
        self.user.save()

        social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='12345',
            secret='54321',
        )
        social_account = SocialAccount.objects.create(
            user=self.user,
            provider='github',
            uid='12345'
        )
        SocialToken.objects.create(
            account=social_account,
            app=social_app,
            token='social-token-xyz'
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'id': 9999,
            'name': 'My Personal Org',
            'login': 'test-user',
            'avatar_url': 'http://avatar',
            'bio': 'My bio'
        }
        mock_get.return_value = mock_resp

        response = self.client.post(url, {'github_org_name': 'test-user'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.user.refresh_from_db()
        self.assertEqual(self.user.github_access_token, 'social-token-xyz')


class GitHubReposViewsTestCase(APITestCaseExpanded):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test-user', password='test-pass'
        )
        self.client = APIClient()
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )

    def test_list_repos_not_linked(self):
        org = self.get_organization(name='Org Not Linked')
        org.github_org_name = None
        org.save()

        url = reverse('github-repos-list', kwargs={'organization_pk': org.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Organization is not linked to GitHub.')

    def test_list_repos_no_token(self):
        org = self.get_organization(name='Org Linked')
        org.github_org_name = 'linked-org'
        org.save()

        self.user.github_access_token = None
        self.user.save()

        url = reverse('github-repos-list', kwargs={'organization_pk': org.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'GitHub account not linked.')

    @patch('organizations.views.requests.get')
    def test_list_repos_success_personal(self, mock_get):
        org = self.get_organization(name='Org Linked')
        org.github_org_name = 'test-user'
        org.save()

        self.user.github_access_token = 'my-token'
        self.user.save()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                'id': 111,
                'name': 'repo-1',
                'full_name': 'test-user/repo-1',
                'description': 'description 1',
                'html_url': 'http://github.com/test-user/repo-1'
            }
        ]
        mock_get.return_value = mock_resp

        url = reverse('github-repos-list', kwargs={'organization_pk': org.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['name'], 'repo-1')

    @patch('organizations.views.requests.get')
    def test_list_repos_fetch_failure(self, mock_get):
        org = self.get_organization(name='Org Linked')
        org.github_org_name = 'test-user'
        org.save()

        self.user.github_access_token = 'my-token'
        self.user.save()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {'message': 'Internal Error'}
        mock_get.return_value = mock_resp

        url = reverse('github-repos-list', kwargs={'organization_pk': org.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], "Failed to fetch repositories for 'test-user'")

    @patch('organizations.views.requests.get')
    def test_list_repos_via_social_token(self, mock_get):
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        org = self.get_organization(name='Org Linked')
        org.github_org_name = 'test-user'
        org.save()

        self.user.github_access_token = None
        self.user.save()

        social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='12345',
            secret='54321',
        )
        social_account = SocialAccount.objects.create(
            user=self.user,
            provider='github',
            uid='12345'
        )
        SocialToken.objects.create(
            account=social_account,
            app=social_app,
            token='social-token-xyz'
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        url = reverse('github-repos-list', kwargs={'organization_pk': org.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.github_access_token, 'social-token-xyz')


