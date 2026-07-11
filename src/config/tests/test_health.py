from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_returns_200_and_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["database"], "ok")

    def test_health_url_reverses(self):
        self.assertEqual(reverse("health-check"), "/health/")

    def test_health_rejects_non_get(self):
        self.assertEqual(self.client.post("/health/").status_code, 405)
