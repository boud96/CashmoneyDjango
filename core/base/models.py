import uuid

import pandas as pd
from django.db import models
from django.db.models import Q, QuerySet, F


class AbstractBaseModel(models.Model):
    """
    This abstract class contains the common fields for all models.
    See https://docs.djangoproject.com/fr/4.0/topics/db/models/#abstract-base-classes
    """
    objects = models.Manager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BankAccount(AbstractBaseModel):
    account_number = models.CharField(max_length=128, blank=False, null=False)
    account_name = models.CharField(max_length=128, null=False, blank=False)
    owners = models.IntegerField(null=False, blank=False, default=1)

    def __str__(self):
        return str(self.account_name)

    @classmethod
    def get_bank_accounts(cls):
        return [(account.id, account.account_name) for account in cls.objects.all()]


class Transaction(AbstractBaseModel):
    WNI_CHOICES = [
        ('want', 'Want'),
        ('investment', 'Investment'),
        ('need', 'Need'),
        ('other', 'Other'),
    ]

    @classmethod
    def get_field_names(cls) -> list:
        return [field.name for field in cls._meta.get_fields()]

    @classmethod
    def get_transactions_from_db(cls, filter_params: dict) -> QuerySet:
        # TODO: Add more filters
        # If filter is used but not added here, raise an error
        expected_filter_keys = [
            "date_from",
            "date_to",
            "category",
            "subcategory",
            "show_ignored",
            "bank_account"
        ]

        date_from = filter_params.get("date_from")
        date_to = filter_params.get("date_to")
        categories = filter_params.get("category")
        subcategories = filter_params.get("subcategory")
        show_ignored = filter_params.get("show_ignored", False)
        bank_accounts = filter_params.get("bank_account")

        extra_keys = [key for key in filter_params if key not in expected_filter_keys]

        if extra_keys:
            raise ValueError(f"Unexpected filter parameters: {', '.join(extra_keys)}")

        query = Q()
        if date_from is not None:
            query &= Q(date_of_transaction__gte=date_from)
        if date_to is not None:
            query &= Q(date_of_transaction__lte=date_to)
        if categories is not None:
            if "None" in categories:
                categories = [cat for cat in categories if cat != "None"]
                query &= (Q(subcategory__category__in=categories) | Q(subcategory__category__isnull=True))
            else:
                query &= Q(subcategory__category__in=categories)
        if subcategories is not None:
            if "None" in subcategories:
                subcategories = [subcat for subcat in subcategories if subcat != "None"]
                query &= (Q(subcategory__in=subcategories) | Q(subcategory__isnull=True))
            else:
                query &= Q(subcategory__in=subcategories)

        if not show_ignored:
            query &= ~Q(ignore=True)

        if bank_accounts is not None:
            if "None" in bank_accounts:
                bank_accounts = [account for account in bank_accounts if account != "None"]
                query &= (Q(bank_account__in=bank_accounts) | Q(bank_account__isnull=True))
            else:
                query &= Q(bank_account__in=bank_accounts)

        field_names = cls.get_field_names()
        related_fields = [  # TODO: Remove or something, not needed?
            "subcategory__name",
            "subcategory__category__name",
            "bank_account__account_name"
        ]

        annotation = {
            "subcategory_name": F("subcategory__name"),
            "category_name": F("subcategory__category__name"),
            "account_name": F("bank_account__account_name")
        }

        return (
            cls.objects.filter(query)
            .annotate(**annotation)
            .values(*field_names, *related_fields, "subcategory_name", "category_name", "account_name")
        )

    @classmethod
    def get_transactions_as_dataframe(cls, filter_params: dict) -> pd.DataFrame:
        transactions = list(cls.get_transactions_from_db(filter_params))

        if not transactions:
            return pd.DataFrame(columns=cls.get_field_names())

        return pd.DataFrame.from_records(transactions)

    def get_tags(self):
        return ", ".join([tag.tag.name for tag in self.transactiontag_set.all()])

    get_tags.short_description = 'Tags'

    original_id = models.CharField(max_length=128, null=True, blank=True)

    date_of_submission = models.DateTimeField(null=True, blank=True)
    date_of_transaction = models.DateTimeField(null=False, blank=False)

    bank_account = models.ForeignKey("BankAccount", on_delete=models.CASCADE, null=True, blank=True)

    counterparty_account_number = models.CharField(max_length=128, null=True, blank=True)
    counterparty_name = models.CharField(max_length=128, null=True, blank=True)

    transaction_type = models.CharField(max_length=128, null=True, blank=True)
    variable_symbol = models.CharField(max_length=128, null=True, blank=True)
    specific_symbol = models.CharField(max_length=128, null=True, blank=True)
    constant_symbol = models.CharField(max_length=128, null=True, blank=True)

    counterparty_note = models.TextField(null=True, blank=True)
    my_note = models.TextField(null=True, blank=True)
    other_note = models.TextField(null=True, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False)
    currency = models.CharField(max_length=3, null=False, blank=False)
    subcategory = models.ForeignKey("Subcategory", on_delete=models.CASCADE, null=True, blank=True)
    want_need_investment = models.CharField(max_length=128, choices=WNI_CHOICES, null=True, blank=True)
    ignore = models.BooleanField(default=False)

    def __str__(self):
        counterparty = self.counterparty_name if self.counterparty_name else ""
        return f"{self.date_of_transaction} - {self.currency}{self.amount} - {counterparty}"


class Category(AbstractBaseModel):
    name = models.CharField(max_length=128, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Subcategory(AbstractBaseModel):
    name = models.CharField(max_length=128, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.category})"


class Tag(AbstractBaseModel):
    name = models.CharField(max_length=128, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class TransactionTag(AbstractBaseModel):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.transaction} - {self.tag}"


class Keyword(AbstractBaseModel):
    value = models.CharField(max_length=128, null=False, blank=False)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE)
    want_need_investment = models.CharField(max_length=128, choices=Transaction.WNI_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.value} - {self.subcategory}"


class CSVMapping(AbstractBaseModel):
    name = models.CharField(max_length=128, null=False, blank=False)
    mapping_json = models.JSONField(null=False, blank=False)

    @classmethod
    def get_csv_mappings(cls) -> list:
        return cls.objects.all()

    def __str__(self):
        return self.name
