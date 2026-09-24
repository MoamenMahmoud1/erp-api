from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from accounts.models import RoleProfile
from common.services.mutation_authorization import (
    MutationAuthorizationService,
    MutationDecision,
)


class MutationAuthorizationServiceTests(SimpleTestCase):
    def make_user(self, *, direct_permission=True, superuser=False, user_id=1):
        user = Mock()
        user.pk = user_id
        user.is_authenticated = True
        user.is_superuser = superuser
        user.has_perm.return_value = direct_permission
        return user

    @patch.object(RoleProfile, "requires_shift_for_user", return_value=False)
    def test_direct_permission_allows_direct_operation(self, _requires_shift):
        actor = self.make_user(direct_permission=True)

        decision = MutationAuthorizationService.decide(
            actor=actor,
            resource="invoice",
            action="update",
            direct_permission="invoices.change_invoice",
        )

        self.assertEqual(decision.decision, MutationDecision.DIRECT)
        self.assertIsNone(decision.manager_id)

    @patch.object(RoleProfile, "requires_shift_for_user", return_value=True)
    @patch.object(
        MutationAuthorizationService,
        "approval_manager_for",
        return_value=SimpleNamespace(pk=22),
    )
    def test_representative_with_direct_permission_is_routed_to_approval(self, _manager, _requires_shift):
        actor = self.make_user(direct_permission=True)

        decision = MutationAuthorizationService.decide(
            actor=actor,
            resource="invoice",
            action="update",
            direct_permission="invoices.change_invoice",
        )

        self.assertEqual(decision.decision, MutationDecision.REQUEST_APPROVAL)
        self.assertEqual(decision.manager_id, 22)

    @patch.object(RoleProfile, "requires_shift_for_user", return_value=True)
    @patch.object(
        MutationAuthorizationService,
        "approval_manager_for",
        return_value=SimpleNamespace(pk=22),
    )
    def test_representative_without_direct_permission_can_request_approval(self, _manager, _requires_shift):
        actor = self.make_user(direct_permission=False)

        decision = MutationAuthorizationService.decide(
            actor=actor,
            resource="vehicle",
            action="update",
            direct_permission="inventory.change_stocklocation",
        )

        self.assertEqual(decision.decision, MutationDecision.REQUEST_APPROVAL)
        self.assertEqual(decision.manager_id, 22)

    @patch.object(RoleProfile, "requires_shift_for_user", return_value=False)
    @patch.object(
        MutationAuthorizationService,
        "approval_manager_for",
        return_value=SimpleNamespace(pk=22),
    )
    def test_user_without_permission_cannot_request_for_non_approval_role(self, _manager, _requires_shift):
        actor = self.make_user(direct_permission=False)

        decision = MutationAuthorizationService.decide(
            actor=actor,
            resource="invoice",
            action="delete",
            direct_permission="invoices.delete_invoice",
        )

        self.assertEqual(decision.decision, MutationDecision.DENIED)

    @patch.object(RoleProfile, "requires_shift_for_user", return_value=True)
    @patch.object(
        MutationAuthorizationService,
        "approval_manager_for",
        return_value=None,
    )
    def test_approval_required_without_eligible_manager_is_denied(self, _manager, _requires_shift):
        actor = self.make_user(direct_permission=True)

        decision = MutationAuthorizationService.decide(
            actor=actor,
            resource="invoice",
            action="delete",
            direct_permission="invoices.delete_invoice",
        )

        self.assertEqual(decision.decision, MutationDecision.DENIED)
        self.assertIn("no eligible manager", decision.reason)
