"""
Testa a timezone explicita do cron do scheduler de releases.

Sem timezone explicita, BackgroundScheduler e CronTrigger usam a tz do OS
do container. Em container UTC a "meia-noite" dispara 00:00 UTC; em
container America/Sao_Paulo dispara 00:00 BRT. A janela de dados do job
(get_releases_and_create_results) e computada com timezone.now() do Django,
que respeita settings.TIME_ZONE. Gatilho e janela precisam ficar alinhados:
o trigger deve usar settings.TIME_ZONE explicitamente.
"""

from django.conf import settings
from django.test import TestCase

from releases import jobs


class ReleaseCronTriggerTimezoneTestCase(TestCase):
    def test_build_release_cron_trigger_uses_settings_timezone(self):
        """O CronTrigger do job deve usar settings.TIME_ZONE explicito."""
        trigger = jobs.build_release_cron_trigger()

        self.assertEqual(str(trigger.timezone), settings.TIME_ZONE)
        self.assertEqual(str(trigger.timezone), "America/Sao_Paulo")

    def test_build_release_scheduler_uses_settings_timezone(self):
        """O BackgroundScheduler do job deve usar settings.TIME_ZONE."""
        scheduler = jobs.build_release_scheduler()

        self.assertEqual(str(scheduler.timezone), settings.TIME_ZONE)
        self.assertEqual(str(scheduler.timezone), "America/Sao_Paulo")
