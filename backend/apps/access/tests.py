from __future__ import annotations

from rest_framework.test import APITestCase

from apps.access.models import Organization
from apps.access.services import issue_token


class SuperuserOrganizationAccessTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Admin Org", slug="admin-org")
        self.user = self._create_superuser()
        token = issue_token(user=self.user, created_by=self.user, label="test-login")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.key}")

    def _create_superuser(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
            default_organization=self.organization,
        )

    def test_me_view_resolves_default_organization_without_membership(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["organization"], self.organization.slug)

    def test_superuser_can_create_strategy_from_default_organization_context(self):
        response = self.client.post(
            "/api/strategies/",
            {
                "name": "Golden Cross",
                "description": "Created by superuser without explicit membership.",
                "change_summary": "Initial version",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Golden Cross")
