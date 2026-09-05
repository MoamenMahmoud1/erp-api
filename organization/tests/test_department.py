from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from organization.models import Company, Department, Site


class DepartmentModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")

    def create_site(self, *, code, site_type):
        return Site.objects.create(
            company=self.company,
            code=code,
            name=code,
            site_type=site_type,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )

    def create_department(self, *, code, site=None):
        return Department.objects.create(
            company=self.company,
            site=site,
            code=code,
            name=code,
        )

    def test_company_can_have_central_department(self):
        department = self.create_department(code="LEGAL")
        self.assertIsNone(department.site)

    def test_head_office_and_branch_can_have_departments(self):
        head_office = self.create_site(code="HQ-01", site_type=Site.Type.HEAD_OFFICE)
        branch = self.create_site(code="BR-01", site_type=Site.Type.BRANCH)

        head_office_department = self.create_department(code="HQ-HR", site=head_office)
        branch_department = self.create_department(code="BR-HR", site=branch)

        self.assertEqual(head_office_department.site, head_office)
        self.assertEqual(branch_department.site, branch)

    def test_store_cannot_have_department(self):
        store = self.create_site(code="ST-01", site_type=Site.Type.STORE)
        with self.assertRaises(ValidationError) as raised:
            self.create_department(code="ST-HR", site=store)
        self.assertIn("site", raised.exception.message_dict)

    def test_department_normalizes_code(self):
        department = self.create_department(code=" hr ")
        self.assertEqual(department.code, "HR")

    def test_department_rejects_code_containing_only_whitespace(self):
        with self.assertRaises(ValidationError) as raised:
            self.create_department(code="   ")
        self.assertIn("code", raised.exception.message_dict)

    def test_department_code_is_unique_across_company(self):
        branch = self.create_site(code="BR-01", site_type=Site.Type.BRANCH)
        self.create_department(code="HR")

        with self.assertRaises(ValidationError):
            self.create_department(code="hr", site=branch)

    def test_database_enforces_department_code_uniqueness(self):
        self.create_department(code="HR")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Department.objects.bulk_create(
                    [
                        Department(
                            company=self.company,
                            code="hr",
                            name="Duplicate HR",
                        )
                    ]
                )
