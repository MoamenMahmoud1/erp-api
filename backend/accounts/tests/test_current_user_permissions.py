from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.api.views.current_user import CurrentUserView


class CurrentUserPermissionsAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="me-permissions-user",
            email="me-permissions@example.com",
            password="StrongPass123!",
        )
        permission = Permission.objects.get(
            content_type__app_label="products",
            codename="view_product",
        )
        self.user.user_permissions.add(permission)
        self.factory = APIRequestFactory()

    def test_current_user_returns_effective_permissions(self):
        request = self.factory.get("/api/v1/auth/me/")
        force_authenticate(request, user=self.user)
        response = CurrentUserView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role_level"], 0)
        self.assertIn("products.view_product", response.data["permissions"])
