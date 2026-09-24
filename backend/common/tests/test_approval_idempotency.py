from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Employee, RoleProfile
from auditlog.models import AuditEvent
from common.api.approval_requests import ApprovalRequestListCreateView, ApprovalReviewView
from inventory.models import StockLocation


class ApprovalIdempotencyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company_site = None

        from organization.models import Company, Site

        company = Company.objects.create(name="Approval Test Company")
        site = Site.objects.create(
            company=company,
            code="APP-AP",
            name="Approval Test Branch",
            site_type=Site.Type.BRANCH,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )

        manager_group = Group.objects.create(name="Approval Manager")
        RoleProfile.objects.create(
            group=manager_group,
            name="Approval Manager",
            level=20,
            scope=RoleProfile.Scope.SITE,
            requires_shift=False,
        )
        rep_group = Group.objects.create(name="Approval Rep")
        RoleProfile.objects.create(
            group=rep_group,
            name="Approval Rep",
            level=10,
            scope=RoleProfile.Scope.SITE,
            requires_shift=True,
        )

        self.manager = User.objects.create_user(
            username="approval-manager",
            password="StrongPass123!",
            is_staff=True,
        )
        self.manager.groups.add(manager_group)
        manager_employee = Employee.objects.create(user=self.manager, work_site=site)

        self.rep = User.objects.create_user(
            username="approval-rep",
            password="StrongPass123!",
            is_staff=True,
        )
        self.rep.groups.add(rep_group)
        Employee.objects.create(user=self.rep, work_site=site, manager=manager_employee)

        permissions = Permission.objects.filter(
            content_type__app_label="inventory",
            codename__in=("transfer_stock", "view_stocklocation", "view_stockbalance"),
        )
        self.rep.user_permissions.set(permissions.filter(codename__in=("transfer_stock", "view_stocklocation", "view_stockbalance")))

        self.vehicle = StockLocation.objects.create(
            name="Approval Van",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.rep,
            site=site,
        )
        self.factory = APIRequestFactory()

    def _create_request(self, key):
        request = self.factory.post(
            "/api/v1/approvals/",
            {
                "target_type": "vehicle",
                "target_id": self.vehicle.pk,
                "operation": "update",
                "payload": {"name": "Renamed Van"},
                "reason": "Rename for route assignment",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        force_authenticate(request, user=self.rep)
        return ApprovalRequestListCreateView.as_view()(request)

    def test_request_replay_does_not_create_duplicate_approval(self):
        first = self._create_request("approval-request-1")
        self.assertEqual(first.status_code, 201)
        second = self._create_request("approval-request-1")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["id"], first.data["id"])

        self.assertEqual(
            AuditEvent.objects.filter(
                action="approval.requested",
                entity_type="vehicle",
                entity_id=self.vehicle.pk,
            ).count(),
            1,
        )
        self.assertEqual(self.vehicle.refresh_from_db(), None)
        self.assertEqual(self.vehicle.name, "Approval Van")

        review_request = self.factory.post(
            f"/api/v1/approvals/{first.data['id']}/approve/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="approval-review-1",
        )
        force_authenticate(review_request, user=self.manager)
        approved = ApprovalReviewView.as_view()(review_request, approval_event_id=first.data["id"], decision="approve")
        self.assertEqual(approved.status_code, 200)

        replay_request = self.factory.post(
            f"/api/v1/approvals/{first.data['id']}/approve/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="approval-review-1",
        )
        force_authenticate(replay_request, user=self.manager)
        replayed = ApprovalReviewView.as_view()(replay_request, approval_event_id=first.data["id"], decision="approve")
        self.assertEqual(replayed.status_code, 200)
        self.assertEqual(replayed.data["decision_event_id"], approved.data["decision_event_id"])

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.name, "Renamed Van")
        self.assertEqual(
            AuditEvent.objects.filter(
                action="approval.approved",
                metadata__approval_id=first.data["id"],
            ).count(),
            1,
        )
