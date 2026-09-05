from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from organization.models import Company, Site


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
        site = self.create_site(code=" cai-01 ", site_type=Site.Type.BRANCH)
        self.assertEqual(site.code, "CAI-01")
        self.assertEqual(site.country_code, "EG")

    def test_site_rejects_code_containing_only_whitespace(self):
        with self.assertRaises(ValidationError) as raised:
            self.create_site(code="   ", site_type=Site.Type.BRANCH)
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
        self.create_site(code="HQ-01", site_type=Site.Type.HEAD_OFFICE)
        with self.assertRaises(ValidationError):
            self.create_site(code="HQ-02", site_type=Site.Type.HEAD_OFFICE)

    def test_site_code_is_case_insensitively_unique(self):
        self.create_site(code="BR-01", site_type=Site.Type.BRANCH)
        with self.assertRaises(ValidationError):
            self.create_site(code="br-01", site_type=Site.Type.BRANCH)

    def test_store_can_belong_to_branch(self):
        branch = self.create_site(code="BR-01", site_type=Site.Type.BRANCH)
        store = self.create_site(
            code="ST-01",
            site_type=Site.Type.STORE,
            parent=branch,
        )
        self.assertEqual(store.parent, branch)

    def test_store_can_belong_directly_to_company(self):
        store = self.create_site(code="ST-01", site_type=Site.Type.STORE)
        self.assertIsNone(store.parent)

    def test_branch_cannot_have_parent(self):
        first_branch = self.create_site(code="BR-01", site_type=Site.Type.BRANCH)
        with self.assertRaises(ValidationError) as raised:
            self.create_site(
                code="BR-02",
                site_type=Site.Type.BRANCH,
                parent=first_branch,
            )
        self.assertIn("parent", raised.exception.message_dict)

    def test_store_parent_must_be_branch(self):
        head_office = self.create_site(code="HQ-01", site_type=Site.Type.HEAD_OFFICE)
        with self.assertRaises(ValidationError) as raised:
            self.create_site(
                code="ST-01",
                site_type=Site.Type.STORE,
                parent=head_office,
            )
        self.assertIn("parent", raised.exception.message_dict)

    def test_database_rejects_branch_parent_when_validation_is_bypassed(self):
        first_branch = self.create_site(code="BR-01", site_type=Site.Type.BRANCH)
        second_branch = self.create_site(code="BR-02", site_type=Site.Type.BRANCH)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Site.objects.filter(pk=second_branch.pk).update(parent=first_branch)
