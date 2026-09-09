from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from accounting.tasks import warm_analytics_reports


class AnalyticsTaskTests(SimpleTestCase):
    @patch("accounting.tasks.dashboard_overview")
    def test_warm_analytics_reports_uses_requested_date_window(self, dashboard_overview):
        warm_analytics_reports.run(as_of=date(2026, 9, 8), lookback_days=7)
        dashboard_overview.assert_called_once_with(
            date_from=date(2026, 9, 2),
            date_to=date(2026, 9, 8),
        )
