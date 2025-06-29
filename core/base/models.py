import uuid

import pandas as pd
from django.db import models
from django.db.models import Q, QuerySet, F, ExpressionWrapper, DecimalField
from multiselectfield import MultiSelectField


# TODO: Add plural names


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
        return cls.objects.all()


class Transaction(AbstractBaseModel):
    WNI_CHOICES = [
        ("want", "Want"),
        ("investment", "Investment"),
        ("need", "Need"),
        ("other", "Other"),
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
            "recalculate_by_owners",
            "bank_account",
        ]

        date_from = filter_params.get("date_from")
        date_to = filter_params.get("date_to")
        categories = filter_params.get("category")
        subcategories = filter_params.get("subcategory")
        show_ignored = filter_params.get("show_ignored", False)
        recalculate_by_owners = filter_params.get("recalculate_by_owners", False)
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
                query &= Q(subcategory__category__in=categories) | Q(
                    subcategory__category__isnull=True
                )
            else:
                query &= Q(subcategory__category__in=categories)
        if subcategories is not None:
            if "None" in subcategories:
                subcategories = [subcat for subcat in subcategories if subcat != "None"]
                query &= Q(subcategory__in=subcategories) | Q(subcategory__isnull=True)
            else:
                query &= Q(subcategory__in=subcategories)

        if not show_ignored:
            query &= ~Q(ignore=True)

        if bank_accounts is not None:
            if "None" in bank_accounts:
                bank_accounts = [
                    account for account in bank_accounts if account != "None"
                ]
                query &= Q(bank_account__in=bank_accounts) | Q(
                    bank_account__isnull=True
                )
            else:
                query &= Q(bank_account__in=bank_accounts)

        field_names = cls.get_field_names()
        related_fields = [
            "subcategory__name",
            "subcategory__category__name",
            "bank_account__account_name",
            "bank_account__owners",
        ]

        effective_amount = F("amount")
        if recalculate_by_owners:
            effective_amount = ExpressionWrapper(
                F("amount") / F("bank_account__owners"),
                output_field=DecimalField(max_digits=2, decimal_places=2),
            )

        annotation = {
            "subcategory_name": F("subcategory__name"),
            "category_name": F("subcategory__category__name"),
            "account_name": F("bank_account__account_name"),
            "owners": F("bank_account__owners"),
            "effective_amount": effective_amount,
        }

        transactions = (
            cls.objects.filter(query)
            .annotate(**annotation)
            .values(
                *field_names,
                *related_fields,
                "subcategory_name",
                "category_name",
                "account_name",
                "amount",
                "effective_amount",
            )
        ).order_by("-date_of_transaction")

        return transactions

    @classmethod
    def get_transactions_as_dataframe(cls, filter_params: dict) -> pd.DataFrame:
        transactions = list(cls.get_transactions_from_db(filter_params))

        if not transactions:
            return pd.DataFrame(columns=cls.get_field_names())

        return pd.DataFrame.from_records(transactions)

    def get_tags(self):
        return ", ".join([tag.tag.name for tag in self.transactiontag_set.all()])

    get_tags.short_description = "Tags"

    original_id = models.CharField(max_length=128, null=True, blank=True)

    date_of_submission = models.DateTimeField(null=True, blank=True)
    date_of_transaction = models.DateTimeField(null=False, blank=False)

    bank_account = models.ForeignKey(
        "BankAccount", on_delete=models.CASCADE, null=True, blank=True
    )

    counterparty_account_number = models.CharField(
        max_length=128, null=True, blank=True
    )
    counterparty_name = models.CharField(max_length=128, null=True, blank=True)

    transaction_type = models.CharField(max_length=128, null=True, blank=True)
    variable_symbol = models.CharField(max_length=128, null=True, blank=True)
    specific_symbol = models.CharField(max_length=128, null=True, blank=True)
    constant_symbol = models.CharField(max_length=128, null=True, blank=True)

    counterparty_note = models.TextField(null=True, blank=True)
    my_note = models.TextField(null=True, blank=True)
    other_note = models.TextField(null=True, blank=True)

    amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=False, blank=False
    )
    currency = models.CharField(max_length=3, null=False, blank=False)
    subcategory = models.ForeignKey(
        "Subcategory", on_delete=models.CASCADE, null=True, blank=True
    )
    want_need_investment = models.CharField(
        max_length=128, choices=WNI_CHOICES, null=True, blank=True
    )
    ignore = models.BooleanField(default=False)

    def __str__(self):
        counterparty = self.counterparty_name if self.counterparty_name else ""
        return f"{self.date_of_transaction} - {self.currency}{self.amount} - {counterparty}"


class Category(AbstractBaseModel):
    name = models.CharField(max_length=128, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subcategory(AbstractBaseModel):
    name = models.CharField(max_length=128, null=False, blank=False, unique=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        ordering = ["category__name", "name"]

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
    value = models.CharField(max_length=128, null=False, blank=False, unique=True)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE)
    want_need_investment = models.CharField(
        max_length=128, choices=Transaction.WNI_CHOICES, null=True, blank=True
    )
    ignore = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.value} - {self.subcategory}"


def get_default_bank_account():
    return BankAccount.objects.first().id  # Or another way to get a valid instance


class CSVMapping(AbstractBaseModel):
    name = models.CharField(max_length=128, null=False, blank=False)
    amount = models.CharField(max_length=128, null=True, blank=True)
    header = models.IntegerField(null=True, blank=True, default=0)
    my_note = models.CharField(max_length=128, null=True, blank=True)
    currency = models.CharField(
        max_length=128, null=True, blank=True
    )  # TODO: Related field?
    encoding = models.CharField(
        max_length=128, null=False, blank=False, default="utf-8"
    )
    delimiter = models.CharField(max_length=5, null=False, blank=False, default=",")
    other_note = models.TextField(
        null=True,
        blank=True,
        help_text="Store a list of notes as a comma-separated string.",
    )
    original_id = models.CharField(max_length=128, null=True, blank=True)
    constant_symbol = models.CharField(max_length=128, null=True, blank=True)
    specific_symbol = models.CharField(max_length=128, null=True, blank=True)
    variable_symbol = models.CharField(max_length=128, null=True, blank=True)
    transaction_type = models.CharField(max_length=128, null=True, blank=True)
    counterparty_name = models.CharField(max_length=128, null=True, blank=True)
    counterparty_note = models.CharField(max_length=128, null=True, blank=True)
    date_of_submission_value = models.CharField(max_length=128, null=True, blank=True)
    date_of_submission_format = models.CharField(max_length=128, null=True, blank=True)
    date_of_transaction_value = models.CharField(
        max_length=128, null=False, blank=False
    )
    date_of_transaction_format = models.CharField(
        max_length=128, null=False, blank=False, default="%d.%m.%Y"
    )
    counterparty_account_number = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Can be account number with or without bank code.",
    )
    counterparty_bank_code = models.CharField(max_length=128, null=True, blank=True)

    ALLOWED_FIELDS = [
        "my_note",
        "other_note",
        "counterparty_note",
        "counterparty_name",
        "transaction_type",
        "variable_symbol",
        "specific_symbol",
        "constant_symbol",
    ]
    CATEGORIZATION_CHOICES = [
        (field, field.replace("_", " ").title()) for field in ALLOWED_FIELDS
    ]
    categorization_fields = MultiSelectField(
        choices=CATEGORIZATION_CHOICES,
        blank=True,
        help_text="Select fields you want to use for categorization.",
    )

    @classmethod
    def get_allowed_fields(cls):
        return [
            field.name
            for field in cls._meta.get_fields()
            if field.concrete and not field.is_relation
        ]

    @classmethod
    def get_categorization_choices(cls):
        """Generate choices dynamically from allowed fields."""
        allowed_fields = cls.get_allowed_fields()
        return [(field, field.replace("_", " ").title()) for field in allowed_fields]

    @classmethod
    def get_csv_mappings(cls) -> list:
        return cls.objects.all()

    def __str__(self):
        return self.name

    def set_other_note_list(self, notes: list):
        """Set the other_note field as a comma-separated string from a list."""
        if not isinstance(notes, list):
            raise ValueError("The 'notes' argument must be a list.")
        self.other_note = ",".join(notes)

    def get_other_note_list(self) -> list:
        """Retrieve the other_note field as a list."""
        if not self.other_note:
            return []
        return [note.strip() for note in self.other_note.split(",")]
