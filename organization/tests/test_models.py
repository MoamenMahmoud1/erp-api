from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from organization.models import Company, Department, Site


class CompanyModelTests(TestCase):
    def test_database_allows_only_one_company(self):
        Company.objects.create(name="First Company")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Company.objects.create(name="Second Company")


class SiteModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")

    def create_site(self, *, code, site_type, parent=None):
        return Site.objects.create(
            company=self.company,
            parent=parent,
            code=code,
            name=code,
            site_type=site_type,
            address_line_1="Test address",
            city="Cairo",
            country_code="eg",
        )

    def test_site_normalizes_code_and_country_code(self):
        site = self.create_site(
            code=" cai-01 ",
            site_type=Site.Type.BRANCH,
        )

        self.assertEqual(site.code, "CAI-01")
        self.assertEqual(site.country_code, "EG")

    def test_site_rejects_code_containing_only_whitespace(self):
        with self.assertRaises(ValidationError) as raised:
            self.create_site(
                code="   ",
                site_type=Site.Type.BRANCH,
            )

        self.assertIn("code", raised.exception.message_dict)

    def test_site_rejects_country_code_containing_only_whitespace(self):
        with self.assertRaises(ValidationError) as raised:
            Site.objects.create(
                company=self.company,
                code="BR-01",
                name="Test branch",
                site_type=Site.Type.BRANCH,
                address_line_1="Test address",
                city="Cairo",
                country_code="  ",
            )

        self.assertIn("country_code", raised.exception.message_dict)

    def test_site_rejects_invalid_country_code_format(self):
        for country_code in ("E", "123", "E1"):
            with self.subTest(country_code=country_code):
                with self.assertRaises(ValidationError) as raised:
                    Site.objects.create(
                        company=self.company,
                        code=f"BR-{country_code}",
                        name="Test branch",
                        site_type=Site.Type.BRANCH,
                        address_line_1="Test address",
                        city="Cairo",
                        country_code=country_code,
                    )

                self.assertIn("country_code", raised.exception.message_dict)

    def test_company_can_have_only_one_head_office(self):
        self.create_site(
            code="HQ-01",
            site_type=Site.Type.HEAD_OFFICE,
        )

        with self.assertRaises(ValidationError):
            self.create_site(
                code="HQ-02",
                site_type=Site.Type.HEAD_OFFICE,
            )

    def test_site_code_is_case_insensitively_unique(self):
        self.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )

        with self.assertRaises(ValidationError):
            self.create_site(
                code="br-01",
                site_type=Site.Type.BRANCH,
            )

    def test_store_can_belong_to_branch(self):
        branch = self.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )

        store = self.create_site(
            code="ST-01",
            site_type=Site.Type.STORE,
            parent=branch,
        )

        self.assertEqual(store.parent, branch)

    def test_store_can_belong_directly_to_company(self):
        store = self.create_site(
            code="ST-01",
            site_type=Site.Type.STORE,
        )

        self.assertIsNone(store.parent)

    def test_branch_cannot_have_parent(self):
        first_branch = self.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )

        with self.assertRaises(ValidationError) as raised:
            self.create_site(
                code="BR-02",
                site_type=Site.Type.BRANCH,
                parent=first_branch,
            )

        self.assertIn("parent", raised.exception.message_dict)

    def test_store_parent_must_be_branch(self):
        head_office = self.create_site(
            code="HQ-01",
            site_type=Site.Type.HEAD_OFFICE,
        )

        with self.assertRaises(ValidationError) as raised:
            self.create_site(
                code="ST-01",
                site_type=Site.Type.STORE,
                parent=head_office,
            )

        self.assertIn("parent", raised.exception.message_dict)

    def test_database_rejects_branch_parent_when_validation_is_bypassed(self):
        first_branch = self.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )
        second_branch = self.create_site(
            code="BR-02",
            site_type=Site.Type.BRANCH,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Site.objects.filter(pk=second_branch.pk).update(
                    parent=first_branch,
                )


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
        head_office = self.create_site(
            code="HQ-01",
            site_type=Site.Type.HEAD_OFFICE,
        )
        branch = self.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )

        head_office_department = self.create_department(
            code="HQ-HR",
            site=head_office,
        )
        branch_department = self.create_department(
            code="BR-HR",
            site=branch,
        )

        self.assertEqual(head_office_department.site, head_office)
        self.assertEqual(branch_department.site, branch)

    def test_store_cannot_have_department(self):
        store = self.create_site(
            code="ST-01",
            site_type=Site.Type.STORE,
        )

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
        branch = self.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )
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
