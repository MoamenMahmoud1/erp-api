from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from organization.api.serializers import DepartmentSerializer, SiteSerializer
from organization.models import Company, Department, Site


User = get_user_model()


class OrganizationAPITestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="Test Company")
        cls.branch = Site.objects.create(
            company=cls.company,
            code="BR-01",
            name="Cairo Branch",
            site_type=Site.Type.BRANCH,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )
        cls.store = Site.objects.create(
            company=cls.company,
            parent=cls.branch,
            code="ST-01",
            name="Nasr City Store",
            site_type=Site.Type.STORE,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )
        cls.department = Department.objects.create(
            company=cls.company,
            site=cls.branch,
            code="HR",
            name="Human Resources",
        )

        cls.group = Group.objects.create(name="Organization API Test Group")
        cls.user = User.objects.create_user(
            username="organization-api-user",
            email="organization-api@test.com",
        )
        cls.user.groups.add(cls.group)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def grant_permissions(self, *codenames):
        self.group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="organization",
                codename__in=codenames,
            )
        )


class OrganizationPermissionAPITests(OrganizationAPITestBase):
    def test_user_without_model_permission_is_forbidden(self):
        response = self.client.get(
            reverse("organization:site-list")
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_view_permission_allows_site_list(self):
        self.grant_permissions("view_site")

        response = self.client.get(
            reverse("organization:site-list")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_permission_allows_site_creation(self):
        self.grant_permissions("add_site")

        response = self.client.post(
            reverse("organization:site-list"),
            {
                "code": "BR-02",
                "name": "Alexandria Branch",
                "site_type": Site.Type.BRANCH,
                "address_line_1": "Test address",
                "city": "Alexandria",
                "country_code": "EG",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["company"], self.company.pk)
        self.assertEqual(response.data["company_name"], self.company.name)

    def test_company_change_requires_change_permission(self):
        self.grant_permissions("view_company")

        response = self.client.patch(
            reverse("organization:company-detail"),
            {"name": "Changed Company"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OrganizationRepresentationTests(OrganizationAPITestBase):
    def test_site_list_returns_relation_ids_and_names(self):
        self.grant_permissions("view_site")

        response = self.client.get(
            reverse("organization:site-list")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sites = {
            item["code"]: item
            for item in response.data["results"]
        }

        self.assertEqual(sites["ST-01"]["company"], self.company.pk)
        self.assertEqual(
            sites["ST-01"]["company_name"],
            self.company.name,
        )
        self.assertEqual(sites["ST-01"]["parent"], self.branch.pk)
        self.assertEqual(
            sites["ST-01"]["parent_name"],
            self.branch.name,
        )
        self.assertIsNone(sites["BR-01"]["parent"])
        self.assertIsNone(sites["BR-01"]["parent_name"])

    def test_department_list_returns_relation_ids_and_names(self):
        self.grant_permissions("view_department")

        response = self.client.get(
            reverse("organization:department-list")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        department = response.data["results"][0]
        self.assertEqual(department["company"], self.company.pk)
        self.assertEqual(department["company_name"], self.company.name)
        self.assertEqual(department["site"], self.branch.pk)
        self.assertEqual(department["site_name"], self.branch.name)


class OrganizationQueryTests(OrganizationAPITestBase):
    def test_site_serialization_uses_one_query(self):
        queryset = Site.objects.select_related(
            "company",
            "parent",
        )

        with CaptureQueriesContext(connection) as captured_queries:
            data = SiteSerializer(queryset, many=True).data
            self.assertEqual(len(data), 2)

        application_queries = [
            query
            for query in captured_queries.captured_queries
            if not query["sql"].lstrip().upper().startswith("EXPLAIN")
        ]
        self.assertEqual(len(application_queries), 1)

    def test_department_serialization_uses_one_query(self):
        queryset = Department.objects.select_related(
            "company",
            "site",
        )

        with CaptureQueriesContext(connection) as captured_queries:
            data = DepartmentSerializer(queryset, many=True).data
            self.assertEqual(len(data), 1)

        application_queries = [
            query
            for query in captured_queries.captured_queries
            if not query["sql"].lstrip().upper().startswith("EXPLAIN")
        ]
        self.assertEqual(len(application_queries), 1)
