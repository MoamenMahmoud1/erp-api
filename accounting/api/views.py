from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounting.api.serializers import (
    AccountingPeriodSerializer,
    AccountSerializer,
    ExpenseSerializer,
    GeneralLedgerLineSerializer,
    JournalEntrySerializer,
    JournalLineSerializer,
    OpeningBalanceSerializer,
    TrialBalanceRowSerializer,
)
from accounting.models import Account, AccountingPeriod, Expense, JournalEntry
from accounting.services import (
    AccountingPeriodError,
    JournalEntryError,
    close_period,
    create_expense,
    create_opening_balance,
    create_period,
    general_ledger,
    get_default_company,
    post_journal_entry,
    trial_balance,
)
from common.exceptions import InvalidBusinessOperation


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("account_type", "is_active", "parent")
    search_fields = ("code", "name")
    ordering_fields = ("code", "name", "account_type", "created_at")
    ordering = ("code",)

    def get_queryset(self):
        return Account.objects.select_related("company", "parent").filter(
            company_id=get_default_company().pk
        )

    def perform_create(self, serializer):
        serializer.save(company=get_default_company())


class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "head", "options")
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
        serializer = JournalEntrySerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            entry = serializer.save()
        except JournalEntryError as exc:
            raise ValidationError(
                {"detail": str(exc), "code": "accounting_error"}
            ) from exc
        return Response(
            JournalEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        try:
            entry = post_journal_entry(
                entry_id=pk,
                actor_id=request.user.pk,
                company=get_default_company(),
            )
        except JournalEntry.DoesNotExist:
            return Response(
                {"detail": "Journal entry not found.", "code": "not_found"},
                status=404,
            )
        except JournalEntryError as exc:
            return Response(
                {"detail": str(exc), "code": "accounting_error"},
                status=409,
            )
        return Response(JournalEntrySerializer(entry).data)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "head", "options")
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("expense_date", "expense_account", "payment_account")
    search_fields = ("description", "reference")
    ordering_fields = ("expense_date", "amount", "created_at")
    ordering = ("-expense_date", "-id")

    def get_queryset(self):
        return (
            Expense.objects.select_related(
                "company",
                "expense_account",
                "payment_account",
                "created_by",
            )
            .filter(company_id=get_default_company().pk)
        )

    def create(self, request, *args, **kwargs):
        serializer = ExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            expense = create_expense(
                amount=data["amount"],
                expense_account=data["expense_account"].pk,
                payment_account=data["payment_account"].pk,
                expense_date=data["expense_date"],
                description=data["description"],
                reference=data.get("reference", ""),
                created_by_id=request.user.pk,
                company=get_default_company(),
            )
        except (Account.DoesNotExist, InvalidBusinessOperation) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            ExpenseSerializer(expense).data,
            status=status.HTTP_201_CREATED,
        )


class AccountingPeriodViewSet(viewsets.ModelViewSet):
    serializer_class = AccountingPeriodSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "head", "options")
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("is_closed", "start_date", "end_date")
    ordering_fields = ("start_date", "end_date", "created_at")
    ordering = ("-start_date",)

    def get_queryset(self):
        return AccountingPeriod.objects.filter(
            company_id=get_default_company().pk
        ).select_related("company", "closed_by")

    def create(self, request, *args, **kwargs):
        serializer = AccountingPeriodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            period = create_period(
                name=serializer.validated_data["name"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
                company=get_default_company(),
            )
        except AccountingPeriodError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            AccountingPeriodSerializer(period).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        try:
            period = close_period(
                period_id=pk,
                actor_id=request.user.pk,
                company=get_default_company(),
            )
        except AccountingPeriod.DoesNotExist:
            return Response(
                {"detail": "Accounting period not found.", "code": "not_found"},
                status=404,
            )
        except AccountingPeriodError as exc:
            return Response(
                {"detail": str(exc), "code": "accounting_period_error"},
                status=409,
            )
        return Response(AccountingPeriodSerializer(period).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def opening_balance_view(request):
    """Create the company's initial posted opening-balance journal."""
    serializer = OpeningBalanceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    lines = [
        {
            "account_id": line["account"].pk,
            "description": line.get("description", ""),
            "debit": line.get("debit", 0),
            "credit": line.get("credit", 0),
        }
        for line in serializer.validated_data["lines"]
    ]
    try:
        entry = create_opening_balance(
            entry_date=serializer.validated_data["entry_date"],
            lines=lines,
            created_by_id=request.user.pk,
            company=get_default_company(),
        )
    except (JournalEntryError, InvalidBusinessOperation) as exc:
        raise ValidationError({"detail": str(exc)}) from exc
    return Response(
        JournalEntrySerializer(entry).data,
        status=status.HTTP_201_CREATED,
    )


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
    return Response(
        {
            "account": AccountSerializer(account).data,
            "lines": GeneralLedgerLineSerializer(lines, many=True).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trial_balance_view(request):
    rows, total_debit, total_credit = trial_balance(
        date_from=request.query_params.get("from"),
        date_to=request.query_params.get("to"),
    )
    return Response(
        {
            "rows": TrialBalanceRowSerializer(rows, many=True).data,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balanced": total_debit == total_credit,
        }
    )
