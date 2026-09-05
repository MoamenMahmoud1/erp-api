from django.contrib import admin

from accounting.models import Account, JournalEntry, JournalLine


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "company", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("code", "name")


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("number", "entry_date", "description", "status", "company")
    list_filter = ("status", "entry_date")
    search_fields = ("description", "reference")
    readonly_fields = ("number", "posted_at", "posted_by", "created_by")
    inlines = (JournalLineInline,)
