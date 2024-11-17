import uuid

from django.db import models


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
    bank_code = models.CharField(max_length=128, null=True, blank=True)
    account_name = models.CharField(max_length=128, null=False, blank=False)
    owners = models.IntegerField(null=False, blank=False, default=1)

    def __str__(self):
        return str(self.account_name)


class Transaction(AbstractBaseModel):
    WNI_CHOICES = [
        ('want', 'Want'),
        ('investment', 'Investment'),
        ('need', 'Need'),
        ('other', 'Other'),
    ]

    def get_tags(self):
        return ", ".join([tag.tag.name for tag in self.transactiontag_set.all()])
    get_tags.short_description = 'Tags'

    original_id = models.CharField(max_length=128, null=True, blank=True)

    date_of_submission = models.DateTimeField(null=True, blank=True)
    date_of_transaction = models.DateTimeField(null=False, blank=False)

    bank_account = models.ForeignKey("BankAccount", on_delete=models.CASCADE, null=True, blank=True)

    counterparty_account_number = models.CharField(max_length=128, null=True, blank=True)
    counterparty_bank_code = models.CharField(max_length=128, null=True, blank=True)
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

    def __str__(self):
        return f"{self.value} - {self.subcategory}"
