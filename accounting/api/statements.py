from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounting.services.statements import balance_sheet, cash_flow, profit_and_loss


def _can_view_reports(request):
    return request.user.is_superuser or request.user.has_perm("accounting.view_financial_reports")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_and_loss_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    data = profit_and_loss(
        date_from=request.query_params.get("from"),
        date_to=request.query_params.get("to"),
    )
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def balance_sheet_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    as_of = request.query_params.get("as_of")
    if not as_of:
        return Response({"detail": "as_of query parameter is required."}, status=400)
    return Response(balance_sheet(as_of=as_of))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cash_flow_view(request):
    if not _can_view_reports(request):
        return Response({"detail": "You do not have permission to view financial reports."}, status=403)
    return Response(
        cash_flow(
            date_from=request.query_params.get("from"),
            date_to=request.query_params.get("to"),
        )
    )
