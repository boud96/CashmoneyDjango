from django.contrib import admin

from core.base.models import BankAccount, Category, Transaction, Subcategory, Tag, TransactionTag, Keyword, CSVMapping


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "account_name",
        "account_number",
        "bank_code",
    )


class TransactionTagInline(admin.TabularInline):
    model = TransactionTag
    extra = 1

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date_of_transaction",
        "amount",
        "currency",
        "subcategory",
        "want_need_investment",
        "counterparty_name",
        "counterparty_note",
        "my_note",
        "other_note",
        "get_tags"
    )
    inlines = [TransactionTagInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description"
    )


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "category"
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description"
    )


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "subcategory",
    )


@admin.register(CSVMapping)
class CSVMappingAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "mapping_json",
    )