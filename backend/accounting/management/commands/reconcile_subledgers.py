from django.core.management.base import BaseCommand, CommandError

from accounting.services.reconciliation import reconcile_subledgers


class Command(BaseCommand):
    help = "Reconcile operational AR/AP balances against the posted general ledger."

    def handle(self, *args, **options):
        result = reconcile_subledgers()
        mismatches = result["customers"] + result["suppliers"]
        if mismatches:
            for row in mismatches:
                self.stdout.write(self.style.ERROR(str(row)))
            raise CommandError(f"Subledger reconciliation failed with {len(mismatches)} mismatch(es).")

        self.stdout.write(self.style.SUCCESS("AR/AP subledgers reconcile with the posted general ledger."))
