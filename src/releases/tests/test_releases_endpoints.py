from datetime import date, timedelta

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from goals.models import Goal
from organizations.models import Repository
from releases.models import Release
from characteristics.models import (
    CalculatedCharacteristic,
    SupportedCharacteristic,
)
from utils.tests import APITestCaseExpanded


class ReleaseEndpointsTestCase(APITestCaseExpanded):
    def setUp(self):
        self.client = APIClient()
        self.user = self.get_or_create_test_user()
        self.client.force_authenticate(
            self.user, token=Token.objects.create(user=self.user)
        )

        self.org = self.get_organization()
        self.product = self.get_product(self.org)
        self.goal = Goal.objects.create(
            created_at=date.today(),
            created_by_id=self.user.id,
            product=self.product,
            data={
                'reliability': 53,
                'maintainability': 53
            },
        )
        self.url_default = f'/api/v1/organizations/{self.org.id}/products/{self.product.id}/release/'

    def test_create_new_release_without_description(self):
        data = {
            'release_name': 'testezada',
            'start_at': '2023-11-24',
            'end_at': '2023-11-25',
            'goal': self.goal.id,
        }

        response = self.client.post(
            path=self.url_default, data=data, format='json'
        )
        self.assertEqual(response.status_code, 201)

        response_json = response.json()
        self.assertEqual(response_json['release_name'], 'testezada')
        self.assertEqual(response_json['description'], None)
        self.assertEqual(
            response_json['start_at'], f"{data['start_at']}T00:00:00-03:00"
        )
        self.assertEqual(
            response_json['end_at'], f"{data['end_at']}T00:00:00-03:00"
        )
        self.assertEqual(response_json['created_by'], self.user.id)
        self.assertEqual(response_json['product'], self.product.id)
        self.assertEqual(response_json['goal'], data['goal'])
        self.assertEqual(response_json['description'], None)

    def test_create_new_release_full(self):
        data = {
            'release_name': 'testezada 2',
            'start_at': '2023-11-24',
            'end_at': '2023-11-25',
            'goal': self.goal.id,
            'description': 'Apenas um testezinho',
        }

        response = self.client.post(
            path=self.url_default, data=data, format='json'
        )
        self.assertEqual(response.status_code, 201)

        response_json = response.json()
        self.assertEqual(response_json['description'], 'Apenas um testezinho')

    def test_create_two_releases_with_conflicting_dates(self):
        release1 = {
            'release_name': 'testezada 1',
            'start_at': '2023-11-24',
            'end_at': '2023-11-30',
            'goal': self.goal.id,
            'description': 'Essa tem que dar certo',
        }

        release2 = {
            'release_name': 'testezada 2',
            'start_at': '2023-11-29',
            'end_at': '2023-12-03',
            'goal': self.goal.id,
            'description': 'Essa tem que dar errado',
        }

        response_release1 = self.client.post(
            path=self.url_default, data=release1, format='json'
        )

        response_release2 = self.client.post(
            path=self.url_default, data=release2, format='json'
        )

        self.assertEqual(response_release1.status_code, 201)
        self.assertEqual(response_release2.status_code, 400)

        self.assertEqual(
            response_release2.json()['message'],
            'The start date must be greater than the start date of the previous release',
        )

    def test_create_two_releases_with_conflicting_names(self):
        release1 = {
            'release_name': 'testezada do baum',
            'start_at': '2023-11-24',
            'end_at': '2023-11-30',
            'goal': self.goal.id,
            'description': 'Essa tem que dar certo',
        }

        release2 = {
            'release_name': 'testezada do baum',
            'start_at': '2023-12-01',
            'end_at': '2023-12-03',
            'goal': self.goal.id,
            'description': 'Essa tem que dar errado',
        }

        response_release1 = self.client.post(
            path=self.url_default, data=release1, format='json'
        )

        response_release2 = self.client.post(
            path=self.url_default, data=release2, format='json'
        )

        self.assertEqual(response_release1.status_code, 201)
        self.assertEqual(response_release2.status_code, 400)

        self.assertEqual(
            response_release2.json()['message'],
            'The release name must be unique',
        )

    def test_create_releases_without_name(self):
        data = {
            'start_at': '2023-11-24',
            'end_at': '2023-11-30',
            'goal': self.goal.id,
        }

        response = self.client.post(
            path=self.url_default, data=data, format='json'
        )

        self.assertEqual(response.status_code, 400)

    def test_create_releases_without_goal(self):
        data = {
            'release_name': 'testezada do baum',
            'start_at': '2023-11-24',
            'end_at': '2023-11-30',
        }

        response = self.client.post(
            path=self.url_default, data=data, format='json'
        )

        self.assertEqual(response.status_code, 400)

    def test_create_releases_without_dates(self):
        data = {
            'release_name': 'testezada do baum',
            'goal': self.goal.id,
            'description': 'Essa tem que dar errado',
        }

        response = self.client.post(
            path=self.url_default, data=data, format='json'
        )

        self.assertEqual(response.status_code, 400)

    def test_get_list_releases(self):
        for i in range(3):
            Release.objects.create(
                created_at=date.today(),
                start_at=date.today(),
                end_at=date.today() + timedelta(days=2),
                release_name=f'Release {i}',
                created_by=self.user,
                product=self.product,
                goal=self.goal,
            )

        response = self.client.get(path=self.url_default)
        response_data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['count'], 3)
        self.assertEqual(len(response_data['results']), 3)

    def test_get_list_releases_empty(self):
        response = self.client.get(path=self.url_default)
        response_data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['count'], 0)
        self.assertEqual(len(response_data['results']), 0)

    def test_get_releases_by_id(self):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        response = self.client.get(path=f'{self.url_default}999/')
        response_data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['release_name'], 'Release 999')
        self.assertEqual(response_data['id'], 999)

    def test_get_releases_by_id_not_found(self):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        response = self.client.get(path=f'{self.url_default}1000/')
        self.assertEqual(response.status_code, 404)

    def test_is_valid_release_without_the_existence_of_releases(self):
        data = {
            'nome': 'Release 999',
            'dt-inicial': '2023-11-24',
            'dt-final': '2023-11-30',
        }

        response = self.client.get(
            path=f'{self.url_default}is-valid/?{data["nome"]}&{data["dt-inicial"]}&{data["dt-final"]}',
            data=data,
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['message'],
            'Parametros válidos para criação de Release',
        )

    def test_is_valid_release_with_the_existence_of_releases_and_valid_datas(
        self,
    ):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        data = {
            'nome': 'Release 111',
            'dt-inicial': date.today() + timedelta(days=3),
            'dt-final': date.today() + timedelta(days=4),
        }

        response = self.client.get(
            path=f'{self.url_default}is-valid/?{data["nome"]}&{data["dt-inicial"]}&{data["dt-final"]}',
            data=data,
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['message'],
            'Parametros válidos para criação de Release',
        )

    def test_is_valid_release_with_the_existence_of_releases_and_invalid_dates(
        self,
    ):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        data = {
            'nome': 'Release 111',
            'dt-inicial': date.today(),
            'dt-final': date.today() + timedelta(days=4),
        }

        response = self.client.get(
            path=f'{self.url_default}is-valid/?{data["nome"]}&{data["dt-inicial"]}&{data["dt-final"]}',
            data=data,
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['detail'], 'Já existe uma release neste período'
        )

    def test_is_valid_release_with_the_existence_of_multiple_releases_and_invalid_dates(
        self,
    ):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        Release.objects.create(
            id=998,
            created_at=date.today(),
            start_at=date.today() + timedelta(days=3),
            end_at=date.today() + timedelta(days=4),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        data = {
            'nome': 'Release 111',
            'dt-inicial': date.today(),
            'dt-final': date.today() + timedelta(days=4),
        }

        response = self.client.get(
            path=f'{self.url_default}is-valid/?{data["nome"]}&{data["dt-inicial"]}&{data["dt-final"]}',
            data=data,
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['detail'], 'Já existem múltiplas releases neste período'
        )

    def test_is_valid_release_with_the_existence_of_releases_and_invalid_name(
        self,
    ):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        data = {
            'nome': 'Release 999',
            'dt-inicial': date.today(),
            'dt-final': date.today() + timedelta(days=4),
        }

        response = self.client.get(
            path=f'{self.url_default}is-valid/?{data["nome"]}&{data["dt-inicial"]}&{data["dt-final"]}',
            data=data,
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['detail'], 'Já existe uma release com este nome'
        )

    def test_planned_x_accomplished_no_release_finished(self):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        response = self.client.get(
            path=f'{self.url_default}999/planeed-x-accomplished/'
        )

        self.assertEqual(response.status_code, 200)
        assert 'reliability' in response.json()['planned'].keys()
        assert 'maintainability' in response.json()['planned'].keys()

    def test_planned_x_accomplished_release_finished(self):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        repository = Repository.objects.create(
            id=1,
            name='Msg',
            key='2023-2-Msg',
            product=self.product,
        )

        reliability = SupportedCharacteristic.objects.filter(
            key='reliability'
        ).first()

        maintainability = SupportedCharacteristic.objects.filter(
            key='maintainability'
        ).first()

        CalculatedCharacteristic.objects.create(
            release_id=999,
            characteristic=reliability,
            repository=repository,
            value=1,
        )

        CalculatedCharacteristic.objects.create(
            release_id=999,
            characteristic=maintainability,
            repository=repository,
            value=1,
        )

        response = self.client.get(
            path=f'{self.url_default}999/planeed-x-accomplished/'
        )

        assert response.status_code == 200
        assert response.json()['accomplished'] == {'Msg': [0, 0]}

    def test_get_analysis_data_no_release_finished(self):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        response = self.client.get(
            path=f'{self.url_default}999/analysis_data/'
        )

        planned = [
            {'name': 'reliability', 'value': 0.53},
            {'name': 'maintainability', 'value': 0.53},
        ]

        assert response.status_code == 200
        assert response.json()['planned'] == planned

    def test_get_analysis_data_release_finished(self):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        reliability = SupportedCharacteristic.objects.filter(
            key='reliability'
        ).first()

        maintainability = SupportedCharacteristic.objects.filter(
            key='maintainability'
        ).first()

        repository1 = Repository.objects.create(
            id=1,
            name='Repository_name',
            key='2023-2-Msg',
            product=self.product,
        )

        CalculatedCharacteristic.objects.create(
            release_id=999,
            characteristic=reliability,
            repository=repository1,
            value=1,
        )

        CalculatedCharacteristic.objects.create(
            release_id=999,
            characteristic=maintainability,
            repository=repository1,
            value=1,
        )

        response = self.client.get(
            path=f'{self.url_default}999/analysis_data/'
        )

        accomplished = [
            {
                'repository_name': 'Repository_name',
                'characteristics': [
                    {'name': 'maintainability', 'value': 1.0, 'diff': 0},
                    {'name': 'reliability', 'value': 1.0, 'diff': 0},
                ],
                'norm_diff': 0.8867924528301886
            }
        ]

        assert response.status_code == 200
        assert response.json()['accomplished'] == accomplished

    def test_get_analysis_data_release_not_found(self):
        response = self.client.get(
            path=f'{self.url_default}999/analysis_data/'
        )

        assert response.status_code == 404
        assert response.json()['detail'] == 'Release não encontrada'

    def test_change_release_end_date(
        self,
    ):
        Release.objects.create(
            id=999,
            created_at=date.today(),
            start_at=date.today(),
            end_at=date.today() + timedelta(days=2),
            release_name='Release 999',
            created_by=self.user,
            product=self.product,
            goal=self.goal,
        )

        data = {
            "end_at": "2024-02-05T23:59:59Z"
        }

        response = self.client.put(
            path=f'{self.url_default}999/update-end-at/',
            data=data,
            format='json',
        )

        self.assertEqual(response.status_code, 200)
