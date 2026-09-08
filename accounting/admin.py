from django.contrib import admin

from unfold.admin import ModelAdmin

from accounting.models import Account, JournalEntry, JournalLine


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ("code", "name", "account_type", "company", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("code", "name")
    ordering = ("code",)
    list_select_related = ("company",)


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    list_display = ("number", "entry_date", "description", "status", "company")
    list_filter = ("status", "entry_date")
    search_fields = ("description", "reference")
    ordering = ("-entry_date", "-number")
    list_select_related = ("company", "created_by", "posted_by")
    readonly_fields = ("number", "posted_at", "posted_by", "created_by")
    inlines = (JournalLineInline,)
