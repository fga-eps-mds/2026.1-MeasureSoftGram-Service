import copy
from unittest.mock import patch

from release_configuration.models import ReleaseConfiguration
from utils import staticfiles
from utils.tests import APITestCaseExpanded


class ProductSaveReleaseConfigurationCase(APITestCaseExpanded):
    """
    Garante que salvar um Product novamente nao duplica a
    pre-configuracao "Default pre-config", mesmo quando o
    DEFAULT_PRE_CONFIG do msgram-core muda entre versoes.
    """

    def get_default_release_configs(self, product):
        return ReleaseConfiguration.objects.filter(
            name="Default pre-config",
            product=product,
        )

    def test_product_save_does_not_duplicate_default_pre_config(self):
        org = self.get_organization()
        product = self.get_product(org)

        self.assertEqual(self.get_default_release_configs(product).count(), 1)

        # Simula a mudanca do DEFAULT_PRE_CONFIG entre versoes do core:
        # o payload muda, mas continua valido.
        changed_pre_config = copy.deepcopy(staticfiles.DEFAULT_PRE_CONFIG)
        changed_pre_config["version"] = "next"

        with patch.object(
            staticfiles, "DEFAULT_PRE_CONFIG", changed_pre_config
        ):
            product.name = "Renamed Product"
            product.save()

        self.assertEqual(self.get_default_release_configs(product).count(), 1)
