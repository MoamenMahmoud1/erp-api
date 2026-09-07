from rest_framework import serializers

from accounting.models import Account, AccountingPeriod, Expense, JournalEntry, JournalLine
from accounting.services import create_journal_entry


class AccountSerializer(serializers.ModelSerializer):
    normal_side = serializers.ReadOnlyField()

    class Meta:
        model = Account
        fields = (
            "id",
            "code",
            "name",
            "account_type",
            "parent",
            "is_active",
            "normal_side",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        account_type = attrs.get("account_type", getattr(self.instance, "account_type", None))
        if parent and parent.account_type != account_type:
            raise serializers.ValidationError(
                {"parent": "A child account must use the same account type as its parent."}
            )
        return attrs


class JournalLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalLine
        fields = ("id", "account", "description", "debit", "credit")
        read_only_fields = ("id",)


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = (
            "id",
            "number",
            "entry_date",
            "description",
            "reference",
            "source_type",
            "source_id",
            "status",
            "created_by",
            "posted_by",
            "posted_at",
            "created_at",
            "updated_at",
            "lines",
        )
        read_only_fields = (
            "id",
            "number",
            "status",
            "created_by",
            "posted_by",
            "posted_at",
            "created_at",
            "updated_at",
            "source_type",
            "source_id",
        )

    def create(self, validated_data):
        raw_lines = validated_data.pop("lines")
        lines = [
            {**line, "account_id": line.pop("account").pk}
            for line in raw_lines
        ]
        request = self.context["request"]
        return create_journal_entry(
            created_by_id=request.user.pk,
            entry_date=validated_data["entry_date"],
            description=validated_data.get("description", ""),
            reference=validated_data.get("reference", ""),
            lines=lines,
        )


class GeneralLedgerLineSerializer(serializers.Serializer):
    entry_number = serializers.IntegerField()
    entry_date = serializers.DateField()
    description = serializers.CharField(allow_blank=True)
    reference = serializers.CharField(allow_blank=True)
    debit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)


class TrialBalanceRowSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    account__code = serializers.CharField()
    account__name = serializers.CharField()
    account__account_type = serializers.CharField()
    debit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)


class ExpenseSerializer(serializers.ModelSerializer):
    expense_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    payment_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())

    class Meta:
        model = Expense
        fields = (
            "id",
            "expense_account",
            "payment_account",
            "amount",
            "expense_date",
            "description",
            "reference",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class OpeningBalanceSerializer(serializers.Serializer):
    entry_date = serializers.DateField()
    lines = JournalLineSerializer(many=True)


class AccountingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingPeriod
        fields = (
            "id",
            "name",
            "start_date",
            "end_date",
            "is_closed",
            "closed_by",
            "closed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "is_closed",
            "closed_by",
            "closed_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return attrs
