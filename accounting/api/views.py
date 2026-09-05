from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from accounting.api.serializers import (
    AccountSerializer,
    GeneralLedgerLineSerializer,
    JournalEntrySerializer,
    TrialBalanceRowSerializer,
)
from accounting.models import Account, JournalEntry
from accounting.services import (
    JournalEntryError,
    general_ledger,
    get_default_company,
    post_journal_entry,
    trial_balance,
)


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("account_type", "is_active", "parent")
    search_fields = ("code", "name")
    ordering_fields = ("code", "name", "account_type", "created_at")
    ordering = ("code",)

    def get_queryset(self):
        return Account.objects.select_related("company", "parent").filter(company_id=get_default_company().pk)

    def perform_create(self, serializer):
        serializer.save(company=get_default_company())


class JournalEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("status", "entry_date", "reference", "source_type")
    search_fields = ("description", "reference")
    ordering_fields = ("number", "entry_date", "created_at")
    ordering = ("-entry_date", "-number")

    def get_queryset(self):
        return (
            JournalEntry.objects.select_related("company", "created_by", "posted_by")
            .prefetch_related("lines__account")
            .filter(company_id=get_default_company().pk)
        )

    def create(self, request, *args, **kwargs):
        serializer = JournalEntrySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            entry = serializer.save()
        except JournalEntryError as exc:
            raise ValidationError({"detail": str(exc), "code": "accounting_error"}) from exc
        return Response(JournalEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        try:
            entry = post_journal_entry(entry_id=pk, actor_id=request.user.pk, company=get_default_company())
        except JournalEntry.DoesNotExist:
            return Response({"detail": "Journal entry not found.", "code": "not_found"}, status=404)
        except JournalEntryError as exc:
            return Response({"detail": str(exc), "code": "accounting_error"}, status=409)
        return Response(JournalEntrySerializer(entry).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def general_ledger_view(request):
    account_id = request.query_params.get("account")
    if not account_id:
        return Response({"detail": "account query parameter is required."}, status=400)
    try:
        account, lines = general_ledger(
            account_id=account_id,
            date_from=request.query_params.get("from"),
            date_to=request.query_params.get("to"),
        )
    except Account.DoesNotExist:
        return Response({"detail": "Account not found.", "code": "not_found"}, status=404)
    return Response({"account": AccountSerializer(account).data, "lines": GeneralLedgerLineSerializer(lines, many=True).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trial_balance_view(request):
    rows, total_debit, total_credit = trial_balance(
        date_from=request.query_params.get("from"),
        date_to=request.query_params.get("to"),
    )
    return Response({
        "rows": TrialBalanceRowSerializer(rows, many=True).data,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balanced": total_debit == total_credit,
    })
