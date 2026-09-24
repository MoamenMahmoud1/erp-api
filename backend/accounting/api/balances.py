from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounting.services.balances import (
    customer_aging,
    customer_balances,
    supplier_aging,
    supplier_balances,
)


def _can_view_reports(request):
    return request.user.is_superuser or request.user.has_perm("accounting.view_financial_reports")


def _as_of(request):
    value = request.query_params.get("as_of")
    if not value:
        return None, Response({"detail": "as_of query parameter is required."}, status=400)
    parsed = parse_date(value)
    if parsed is None:
        return None, Response({"detail": "as_of must be a valid ISO date (YYYY-MM-DD)."}, status=400)
    return parsed, None


def _optional_id(request, name):
    value = request.query_params.get(name)
    if value is None:
        return None, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, Response({"detail": f"{name} must be an integer."}, status=400)
    if parsed <= 0:
        return None, Response({"detail": f"{name} must be greater than zero."}, status=400)
    return parsed, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_balances_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    as_of, error = _as_of(request)
    if error:
        return error
    customer_id, error = _optional_id(request, "customer_id")
    if error:
        return error
    return Response({"as_of": as_of, "customers": customer_balances(as_of=as_of, customer_id=customer_id)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def supplier_balances_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    as_of, error = _as_of(request)
    if error:
        return error
    supplier_id, error = _optional_id(request, "supplier_id")
    if error:
        return error
    return Response({"as_of": as_of, "suppliers": supplier_balances(as_of=as_of, supplier_id=supplier_id)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_aging_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    as_of, error = _as_of(request)
    if error:
        return error
    customer_id, error = _optional_id(request, "customer_id")
    if error:
        return error
    return Response({"as_of": as_of, "customers": customer_aging(as_of=as_of, customer_id=customer_id)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def supplier_aging_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    as_of, error = _as_of(request)
    if error:
        return error
    supplier_id, error = _optional_id(request, "supplier_id")
    if error:
        return error
    return Response({"as_of": as_of, "suppliers": supplier_aging(as_of=as_of, supplier_id=supplier_id)})
