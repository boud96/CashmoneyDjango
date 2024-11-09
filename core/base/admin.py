from django.contrib import admin

from core.base.models import BankAccount, Category, Transaction, Subcategory


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "account_name",
        "account_number",
        "bank_code",
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date_of_transaction",
        "amount",
        "currency",
        "counterparty_name",
        "counterparty_note",
        "my_note",
        "other_note"
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description"
    )


@admin.register(Subcategory)
class Subcategory(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "category"
    )