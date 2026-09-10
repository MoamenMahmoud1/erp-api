# accounts/models/__init__.py
from .user import CustomUserModel
from .employee import Employee
from .role import GroupPolicy
from .shift import EmployeeShift

# Backward-compatible import alias; Group is the role identity.
Role = GroupPolicy

__all__ = (
    "CustomUserModel",
    "Employee",
    "GroupPolicy",
    "Role",
    "EmployeeShift",
)
