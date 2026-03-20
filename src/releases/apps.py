from django.apps import AppConfig

from config.settings import AMBIENT_TEST_OR_DEV


class ReleasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'releases'

    def ready(self):
        if not AMBIENT_TEST_OR_DEV:
            from . import jobs

            jobs.check_the_need_to_calculate_releases()
