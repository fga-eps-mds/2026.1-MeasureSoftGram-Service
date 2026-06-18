from unittest.mock import Mock, patch

from django.db.utils import IntegrityError

from characteristics.models import (
    BalanceMatrix,
    CalculatedCharacteristic,
    SupportedCharacteristic,
)
from organizations.management.commands.load_initial_data import (
    BADGE_DEMO_REPOSITORIES,
    Command,
)
from organizations.management.commands.utils import create_balance_matrix
from organizations.models import Organization, Product
from tsqmi.models import TSQMI
from utils.tests import APITestCaseExpanded


class LoadInitialDataBadgeDemoTestCase(APITestCaseExpanded):
    def setUp(self):
        self.command = Command()

    def test_create_badge_demo_repositories_is_idempotent(self):
        repositories = self.command.create_badge_demo_repositories()

        self.assertEqual(set(repositories.keys()), {'A', 'B', 'C', 'D', 'E', 'N/A'})
        self.assertTrue(Organization.objects.filter(name='Badge Demo Organization').exists())

        organization = Organization.objects.get(name='Badge Demo Organization')
        product = Product.objects.get(
            name='Badge Demo Product',
            organization=organization,
        )

        self.assertEqual(product.repositories.count(), len(BADGE_DEMO_REPOSITORIES))

        repositories_again = self.command.create_badge_demo_repositories()
        self.assertEqual(set(repositories_again.keys()), set(repositories.keys()))
        self.assertEqual(product.repositories.count(), len(BADGE_DEMO_REPOSITORIES))

    def test_create_badge_demo_values_populates_expected_counts(self):
        repositories = self.command.create_badge_demo_repositories()

        repository_a = repositories['A']
        TSQMI.objects.create(value=0.01, repository=repository_a)
        CalculatedCharacteristic.objects.create(
            characteristic=SupportedCharacteristic.objects.first(),
            value=0.01,
            repository=repository_a,
        )

        self.command.create_badge_demo_values(repositories)

        expected_characteristic_count = SupportedCharacteristic.objects.count()
        expected_values = {
            item['grade']: item['value'] for item in BADGE_DEMO_REPOSITORIES
        }

        for grade, repository in repositories.items():
            if grade == 'N/A':
                self.assertFalse(repository.calculated_tsqmis.exists())
                self.assertFalse(repository.calculated_characteristics.exists())
                continue

            self.assertEqual(repository.calculated_tsqmis.count(), 1)
            self.assertEqual(
                repository.calculated_characteristics.count(),
                expected_characteristic_count,
            )
            self.assertEqual(
                repository.calculated_tsqmis.first().value,
                expected_values[grade],
            )
            self.assertEqual(
                set(repository.calculated_characteristics.values_list('value', flat=True)),
                {expected_values[grade]},
            )

    def test_handle_enters_badge_demo_branch(
        self,
    ):
        with patch.object(Command, 'create_supported_metrics'), patch.object(
            Command, 'create_suported_measures'
        ), patch.object(Command, 'create_github_suported_measures'), patch.object(
            Command, 'create_supported_subcharacteristics'
        ), patch.object(Command, 'create_supported_characteristics'), patch.object(
            Command, 'create_balance_matrix'
        ), patch.object(Command, 'create_fake_organizations'), patch.object(
            Command, 'create_fake_products'
        ), patch.object(Command, 'create_fake_repositories'), patch.object(
            Command, 'create_fake_collected_metrics'
        ) as mock_create_fake_collected_metrics, patch.object(
            Command, 'create_fake_calculated_measures'
        ), patch.object(
            Command, 'create_fake_calculated_subcharacteristics'
        ), patch.object(Command, 'create_fake_calculated_characteristics'), patch.object(
            Command, 'create_fake_tsqmi_data'
        ) as mock_create_fake_tsqmi_data, patch.object(
            Command, 'create_badge_demo_repositories'
        ) as mock_create_badge_demo_repositories, patch.object(
            Command, 'create_badge_demo_values'
        ) as mock_create_badge_demo_values, patch.object(
            Command, 'create_a_goal'
        ), patch('organizations.management.commands.load_initial_data.Repository.objects.all') as mock_repository_all, patch(
            'organizations.management.commands.load_initial_data.get_user_model'
        ) as mock_get_user_model:
            mock_create_badge_demo_repositories.return_value = {'A': Mock()}
            mock_repository_all.return_value = [Mock()]
            mock_user_model = Mock()
            mock_user_model.objects.create_superuser.side_effect = IntegrityError()
            mock_get_user_model.return_value = mock_user_model

            self.command.handle(fake_data=True)

            mock_create_badge_demo_repositories.assert_called_once()
            mock_create_badge_demo_values.assert_called_once()
            mock_create_fake_collected_metrics.assert_called()
            mock_create_fake_tsqmi_data.assert_called()

    def test_create_balance_matrix_is_idempotent(self):
        characteristics = SupportedCharacteristic.objects.all()

        create_balance_matrix(characteristics)
        count_after_first_run = BalanceMatrix.objects.count()

        create_balance_matrix(characteristics)
        self.assertEqual(BalanceMatrix.objects.count(), count_after_first_run)



