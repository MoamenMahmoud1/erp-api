from accounts.models import RoleProfile


def can_approve_stock_request(*, approver, requester):
    if not approver or not requester or not approver.is_authenticated or not requester.is_authenticated:
        return False
    if approver.pk == requester.pk:
        return False
    if approver.is_superuser:
        return True
    if not approver.has_perm("inventory.approve_stock_transfer"):
        return False

    # Approval must always move upward in the organizational hierarchy.
    # This also supports manager -> manager when managers have different role levels.
    return RoleProfile.level_for_user(approver) > RoleProfile.level_for_user(requester)
