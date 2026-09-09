from django.utils.dateparse import parse_date
from django.utils.timezone import localdate
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from products.models import Product
from products.services.intelligence import product_intelligence


class ProductIntelligencePermission(BasePermission):
    message = "You do not have permission to view product intelligence."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("products.view_product")
        )


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


@extend_schema(
    parameters=[
        OpenApiParameter("as_of", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("lookback_days", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("forecast_days", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("target_stock_days", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("slow_moving_days", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("limit", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("product_id", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
    ],
)
@api_view(["GET"])
@permission_classes([ProductIntelligencePermission])
def product_intelligence_view(request):
    """Return explainable product demand and stock recommendations."""
    as_of_raw = request.query_params.get("as_of")
    as_of = parse_date(as_of_raw) if as_of_raw else localdate()
    if as_of_raw and as_of is None:
        return Response({"detail": "as_of must be a valid ISO date (YYYY-MM-DD)."}, status=400)
    if as_of > localdate():
        return Response({"detail": "as_of must not be in the future."}, status=400)

    lookback_days, error = _positive_int(request, "lookback_days", 30, 365)
    if error:
        return error
    forecast_days, error = _positive_int(request, "forecast_days", 7, 90)
    if error:
        return error
    target_stock_days, error = _positive_int(request, "target_stock_days", 14, 180)
    if error:
        return error
    slow_moving_days, error = _positive_int(request, "slow_moving_days", 60, 365)
    if error:
        return error
    limit, error = _positive_int(request, "limit", 100, 500)
    if error:
        return error

    product_id_raw = request.query_params.get("product_id")
    product_id = None
    if product_id_raw is not None:
        try:
            product_id = int(product_id_raw)
        except (TypeError, ValueError):
            return Response({"detail": "product_id must be an integer."}, status=400)
        if product_id <= 0:
            return Response({"detail": "product_id must be positive."}, status=400)

    return Response(
        product_intelligence(
            as_of=as_of,
            lookback_days=lookback_days,
            forecast_days=forecast_days,
            target_stock_days=target_stock_days,
            slow_moving_days=slow_moving_days,
            limit=limit,
            product_id=product_id,
        )
    )
