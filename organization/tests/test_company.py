from django.db import IntegrityError, transaction
from django.test import TestCase

from organization.models import Company


class CompanyModelTests(TestCase):
    def test_database_allows_only_one_company(self):
        Company.objects.create(name="First Company")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Company.objects.create(name="Second Company")
