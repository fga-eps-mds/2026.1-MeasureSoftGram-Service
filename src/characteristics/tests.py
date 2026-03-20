from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from characteristics.models import BalanceMatrix, SupportedCharacteristic
from characteristics.serializers import BalanceMatrixSerializer


class BalanceMatrixViewSetTest(APITestCase):
    def setUp(self):
        # Create test data
        characteristic1 = SupportedCharacteristic.objects.create(
            key='characteristic1'
        )
        characteristic2 = SupportedCharacteristic.objects.create(
            key='characteristic2'
        )
        characteristic3 = SupportedCharacteristic.objects.create(
            key='characteristic3'
        )

        BalanceMatrix.objects.create(
            source_characteristic=characteristic1,
            target_characteristic=characteristic2,
            relation_type='+',
        )
        BalanceMatrix.objects.create(
            source_characteristic=characteristic2,
            target_characteristic=characteristic1,
            relation_type='+',
        )
        BalanceMatrix.objects.create(
            source_characteristic=characteristic1,
            target_characteristic=characteristic3,
            relation_type='-',
        )
        BalanceMatrix.objects.create(
            source_characteristic=characteristic3,
            target_characteristic=characteristic1,
            relation_type='-',
        )

    def test_list_balance_matrix(self):
        url = '/api/v1/balance-matrix/'

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        expected_data = {
            'count': 3,
            'next': None,
            'previous': None,
            'result': {
                'characteristic1': {
                    '+': ['characteristic2'],
                    '-': ['characteristic3'],
                },
                'characteristic2': {'+': ['characteristic1'], '-': []},
                'characteristic3': {'+': [], '-': ['characteristic1']},
            },
        }

        self.assertEqual(response.json(), expected_data)
