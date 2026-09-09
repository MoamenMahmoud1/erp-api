from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounting.permissions import AccountingReportPermission
from accounting.services.analytics import dashboard_overview, inventory_dashboard, purchase_dashboard, sales_by_employee, sales_dashboard, top_products
from organization.models import Site
from services.organization_scope import visible_site_ids


def _date_range(request):
    date_from = request.query_params.get("from")
    date_to = request.query_params.get("to")
    if date_from and parse_date(date_from) is None:
        return None, None, Response({"detail": "from must be a valid ISO date (YYYY-MM-DD)."}, status=400)
    if date_to and parse_date(date_to) is None:
        return None, None, Response({"detail": "to must be a valid ISO date (YYYY-MM-DD)."}, status=400)
    if date_from and date_to and date_from > date_to:
        return None, None, Response({"detail": "from must not be after to."}, status=400)
    return date_from, date_to, None


def _positive_int(request, name, default, maximum):
    value = request.query_params.get(name)
    if value is None:
        return default, None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None, Response({"detail": f"{name} must be an integer."}, status=400)
    if value <= 0 or value > maximum:
        return None, Response({"detail": f"{name} must be between 1 and {maximum}."}, status=400)
    return value, None


def _site_id(request):
    value = request.query_params.get("site")
    if value is None:
        return None, None
    try:
        site_id = int(value)
    except (TypeError, ValueError):
        return None, Response({"detail": "site must be a positive integer."}, status=400)
    if site_id <= 0:
        return None, Response({"detail": "site must be a positive integer."}, status=400)

    visible_sites = visible_site_ids(request.user)
    site_queryset = Site.objects.filter(pk=site_id)
    if visible_sites is not None:
        site_queryset = site_queryset.filter(pk__in=visible_sites)

    if not site_queryset.exists():
        return None, Response({"detail": "site does not exist or is outside your allowed scope."}, status=403)
    return site_id, None


@api_view(["GET"])
@permission_classes([AccountingReportPermission])
def dashboard_overview_view(request):
    date_from, date_to, error = _date_range(request)
    if error:
        return error
    site_id, error = _site_id(request)
    if error:
        return error
    return Response(
        dashboard_overview(
            date_from=parse_date(date_from) if date_from else None,
            date_to=parse_date(date_to) if date_to else None,
            site_id=site_id,
        )
    )


@api_view(["GET"])
@permission_classes([AccountingReportPermission])
def sales_dashboard_view(request):
    date_from, date_to, error = _date_range(request)
    if error:
        return error
    site_id, error = _site_id(request)
    if error:
        return error
    return Response(sales_dashboard(date_from=date_from, date_to=date_to, site_id=site_id))


@api_view(["GET"])
@permission_classes([AccountingReportPermission])
def purchase_dashboard_view(request):
    date_from, date_to, error = _date_range(request)
    if error:
        return error
    site_id, error = _site_id(request)
    if error:
        return error
    return Response(purchase_dashboard(date_from=date_from, date_to=date_to, site_id=site_id))


@api_view(["GET"])
@permission_classes([AccountingReportPermission])
def inventory_dashboard_view(request):
    threshold, error = _positive_int(request, "low_stock_threshold", 10, 1000000)
    if error:
        return error
    site_id, error = _site_id(request)
    if error:
        return error
    return Response(inventory_dashboard(low_stock_threshold=threshold, site_id=site_id))


@api_view(["GET"])
@permission_classes([AccountingReportPermission])
def top_products_view(request):
    date_from, date_to, error = _date_range(request)
    if error:
        return error
    limit, error = _positive_int(request, "limit", 10, 100)
    if error:
        return error
    site_id, error = _site_id(request)
    if error:
        return error
    return Response({"date_from": date_from, "date_to": date_to, "site_id": site_id, "products": top_products(date_from=date_from, date_to=date_to, limit=limit, site_id=site_id)})


@api_view(["GET"])
@permission_classes([AccountingReportPermission])
def sales_by_employee_view(request):
    date_from, date_to, error = _date_range(request)
    if error:
        return error
    site_id, error = _site_id(request)
    if error:
        return error
    return Response({"date_from": date_from, "date_to": date_to, "site_id": site_id, "employees": sales_by_employee(date_from=date_from, date_to=date_to, site_id=site_id)})
