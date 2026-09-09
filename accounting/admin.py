from django.contrib import admin

from accounting.models import (
    Account,
    AccountingPeriod,
    Expense,
    JournalEntry,
    JournalLine,
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "company", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("code", "name")
    ordering = ("code",)
    list_select_related = ("company",)


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("number", "entry_date", "description", "status", "company")
    list_filter = ("status", "entry_date")
    search_fields = ("description", "reference")
    ordering = ("-entry_date", "-number")
    list_select_related = ("company", "created_by", "posted_by")
    readonly_fields = ("number", "posted_at", "posted_by", "created_by")
    inlines = (JournalLineInline,)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "expense_date",
        "description",
        "amount",
        "expense_account",
        "payment_account",
        "created_by",
    )
    list_filter = ("expense_date", "expense_account", "payment_account")
    search_fields = ("description", "reference", "created_by__username")
    ordering = ("-expense_date", "-id")
    list_select_related = ("expense_account", "payment_account", "created_by", "company")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "start_date",
        "end_date",
        "is_closed",
        "closed_by",
        "closed_at",
    )
    list_filter = ("is_closed", "start_date", "end_date")
    search_fields = ("name", "company__name")
    ordering = ("-start_date",)
    list_select_related = ("company", "closed_by")
    readonly_fields = ("closed_by", "closed_at", "created_at", "updated_at")
