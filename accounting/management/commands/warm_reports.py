from django.core.management.base import BaseCommand
from django.utils import timezone

from accounting.services.analytics import dashboard_overview, inventory_dashboard, purchase_dashboard, sales_dashboard


class Command(BaseCommand):
    help = "Warm the short-lived report cache for common dashboard queries."

    def handle(self, *args, **options):
        today = timezone.localdate()
        dashboard_overview(date_to=today)
        sales_dashboard(date_to=today)
        purchase_dashboard(date_to=today)
        inventory_dashboard()
        self.stdout.write(self.style.SUCCESS("Report cache warmed."))
