from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounting.services.statements import balance_sheet, cash_flow, profit_and_loss


def _can_view_reports(request):
    return request.user.is_superuser or request.user.has_perm("accounting.view_financial_reports")


def _date_params(request, *, require_as_of=False):
    date_from = request.query_params.get("from")
    date_to = request.query_params.get("to")
    as_of = request.query_params.get("as_of")

    if date_from and parse_date(date_from) is None:
        return None, None, Response({"detail": "from must be a valid ISO date (YYYY-MM-DD)."}, status=400)
    if date_to and parse_date(date_to) is None:
        return None, None, Response({"detail": "to must be a valid ISO date (YYYY-MM-DD)."}, status=400)
    if date_from and date_to and date_from > date_to:
        return None, None, Response({"detail": "from must not be after to."}, status=400)
    if require_as_of and not as_of:
        return None, None, Response({"detail": "as_of query parameter is required."}, status=400)
    if as_of and parse_date(as_of) is None:
        return None, None, Response({"detail": "as_of must be a valid ISO date (YYYY-MM-DD)."}, status=400)
    return (date_from, date_to, as_of), None, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_and_loss_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    params, _, error = _date_params(request)
    if error:
        return error
    date_from, date_to, _ = params
    return Response(profit_and_loss(date_from=date_from, date_to=date_to))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def balance_sheet_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    params, _, error = _date_params(request, require_as_of=True)
    if error:
        return error
    _, _, as_of = params
    return Response(balance_sheet(as_of=as_of))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cash_flow_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    params, _, error = _date_params(request)
    if error:
        return error
    date_from, date_to, _ = params
    return Response(cash_flow(date_from=date_from, date_to=date_to))
