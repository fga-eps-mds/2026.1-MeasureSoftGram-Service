"""
Testa o guard de lider unico do scheduler APScheduler.

Com gunicorn multi-worker, releases/apps.py ready() roda uma vez por
worker. Sem um guard, cada worker sobe seu proprio BackgroundScheduler
e o cron get_releases_and_create_results dispara N vezes (uma por
worker), duplicando CalculatedCharacteristic. O guard usa um advisory
lock de sessao do Postgres (pg_try_advisory_lock): so o worker que
adquire o lock starta o scheduler.
"""

from unittest import mock

from django.test import TestCase

from releases import jobs


class SchedulerLockTestCase(TestCase):
    def test_acquire_scheduler_lock_true_when_lock_free(self):
        """Primeiro worker pega o lock -> deve startar o scheduler."""
        with mock.patch("releases.jobs.connection") as conn:
            cursor = (
                conn.cursor.return_value.__enter__.return_value
            )
            cursor.fetchone.return_value = (True,)

            self.assertTrue(jobs.acquire_scheduler_lock())

    def test_acquire_scheduler_lock_false_when_already_held(self):
        """Workers seguintes nao pegam o lock -> nao sobem scheduler."""
        with mock.patch("releases.jobs.connection") as conn:
            cursor = (
                conn.cursor.return_value.__enter__.return_value
            )
            cursor.fetchone.return_value = (False,)

            self.assertFalse(jobs.acquire_scheduler_lock())

    def test_check_the_need_skips_start_when_lock_not_acquired(self):
        """Sem o lock, check_the_need nao chama scheduler.start()."""
        with mock.patch(
            "releases.jobs.acquire_scheduler_lock", return_value=False
        ), mock.patch(
            "releases.jobs.BackgroundScheduler"
        ) as scheduler_cls:
            jobs.check_the_need_to_calculate_releases()
            scheduler_cls.return_value.start.assert_not_called()

    def test_check_the_need_starts_when_lock_acquired(self):
        """Com o lock, check_the_need sobe o scheduler normalmente."""
        with mock.patch(
            "releases.jobs.acquire_scheduler_lock", return_value=True
        ), mock.patch(
            "releases.jobs.register_events"
        ), mock.patch(
            "releases.jobs.BackgroundScheduler"
        ) as scheduler_cls:
            jobs.check_the_need_to_calculate_releases()
            scheduler_cls.return_value.start.assert_called_once()
