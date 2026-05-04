from django.apps import AppConfig
from django.conf import settings


class ReleasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'releases'

    def ready(self):
        if not settings.AMBIENT_TEST_OR_DEV:
            from . import jobs

            jobs.check_the_need_to_calculate_releases()
