import logging

from django.conf import settings
from django.dispatch import receiver

from allauth.socialaccount.signals import social_account_added

from organizations.services import seed_demo_data

logger = logging.getLogger(__name__)


@receiver(social_account_added)
def seed_demo_data_for_demo_account(request, sociallogin, **kwargs):
    """
    Popula o catálogo de dados de demonstração (organizações, produtos e
    repositórios mockados) na primeira vez que a conta de demonstração do
    GitHub (settings.DEMO_GITHUB_USERNAME) faz login.
    """
    account = sociallogin.account

    if account.provider != 'github':
        return

    github_login = account.extra_data.get('login')

    if github_login != settings.DEMO_GITHUB_USERNAME:
        return

    logger.info(
        f'Seeding demo data for GitHub demo account {github_login!r}',
    )
    seed_demo_data(sociallogin.user)
