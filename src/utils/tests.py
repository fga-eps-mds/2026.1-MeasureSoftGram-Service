from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from accounts.models import CustomUser

from organizations.management.commands.load_initial_data import (
    Command as LoadInitialDataCommand,
)
from organizations.models import Organization


class APITestCaseExpanded(APITestCase):
    """
    Classe que agrupa rotinas e métodos que vários tests cases usam
    """

    @classmethod
    def setUpTestData(cls) -> None:
        command = LoadInitialDataCommand()
        command.create_supported_metrics()
        command.create_suported_measures()
        command.create_github_suported_measures()
        command.create_supported_subcharacteristics()
        command.create_supported_characteristics()

    def get_organization(
        self,
        name='Test Organization',
        description='Test Organization Description',
    ):
        return Organization.objects.create(
            name=name,
            description=description,
        )

    def get_product(
        self,
        org: Organization,
        name='Test Product',
        description='Test Product Description',
    ):
        return org.products.create(name=name, description=description)

    def get_repository(
        self,
        product,
        name='Test Repository',
        description='Test Repository Description',
    ):
        return product.repositories.create(
            name=name,
            description=description,
        )

    def get_goal_data(self):
        return {
            'release_name': 'v1.0',
            'start_at': '2020-01-01',
            'end_at': '2021-01-01',
            'changes': [
                {'characteristic_key': 'reliability', 'delta': 1},
                {'characteristic_key': 'maintainability', 'delta': 1},
            ],
        }

    def validate_key(self, key):
        """
        Função auxiliar para validar se a key das
        entidades seguem o padrão de nomeação definido.
        """
        for c in key:
            self.assertTrue(
                c.islower() or c.isalnum() or c == '_',
                msg=(
                    'All characters in key must be lowercase and '
                    f'alphanumeric. The key is {key} and the '
                    f'failed char is {c}'
                ),
            )

    def get_or_create_test_user(self) -> CustomUser:
        """Método que retorna um usuário padrão para os testes"""

        maybe_user = {
            'username': 'test-user',
            'first_name': 'test',
            'last_name': 'user',
            'email': 'test_product_user@email.com',
        }

        check_user = get_user_model().objects.filter(email=maybe_user['email'])
        if not check_user.exists():
            return get_user_model().objects.create(**maybe_user)

        return check_user[0]
