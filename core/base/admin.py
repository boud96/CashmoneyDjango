from django.contrib import admin

from core.base.models import (
    BankAccount,
    Category,
    Transaction,
    Subcategory,
    Tag,
    TransactionTag,
    Keyword,
    CSVMapping,
)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "account_name",
        "account_number",
    )


class TransactionTagInline(admin.TabularInline):
    model = TransactionTag
    extra = 1


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    search_fields = [
        "original_id",
        "date_of_transaction",
        "bank_account__account_name",
        "amount",
        "counterparty_account_number",
        "counterparty_name",
        "counterparty_note",
        "my_note",
        "other_note",
        "currency",
    ]
    list_filter = [
        "bank_account",
        "subcategory__category",
        "subcategory",
        "want_need_investment",
        "ignore",
        "currency",
    ]

    list_display = (
        "date_of_transaction",
        "amount",
        "bank_account",
        "subcategory",
        "want_need_investment",
        "counterparty_name",
        "counterparty_note",
        "my_note",
        "other_note",
        "ignore",
        "currency",
        "get_tags",
    )

    inlines = [TransactionTagInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "category")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("value", "subcategory", "want_need_investment", "ignore")


@admin.register(CSVMapping)
class CSVMappingAdmin(admin.ModelAdmin):
    list_display = ("name", "categorization_fields_display")

    def categorization_fields_display(self, obj):
        """Display the categorization fields as a comma-separated string."""
        return ", ".join(
            [field.replace("_", " ").title() for field in obj.categorization_fields]
        )

    categorization_fields_display.short_description = "Categorization Fields"
