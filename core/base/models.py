from django.contrib import admin
import uuid

from django.db import models


class AbstractBaseModel(models.Model):
    """
    This abstract class contains the common fields for all models.
    See https://docs.djangoproject.com/fr/4.0/topics/db/models/#abstract-base-classes
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class QualityTagValues(models.TextChoices):
    """
    This class contains the default possible values for the quality tag.
    """

    KO = "KO"
    TO_BE_CHECKED = "TO_BE_CHECKED"
    OK = "OK"


def get_quality_tag_field() -> models.CharField:
    return models.CharField(
        max_length=24,
        choices=QualityTagValues.choices,
        default=QualityTagValues.TO_BE_CHECKED,
    )


class ImageAnnotation(AbstractBaseModel):
    image_id = models.CharField(max_length=60, blank=False, null=False)
    label = models.CharField(max_length=60, null=False, blank=False)
    height = models.IntegerField(null=False, blank=False, default=-1)
    width = models.IntegerField(null=False, blank=False, default=-1)
    label_correctness = get_quality_tag_field()
    image_correctness = get_quality_tag_field()

    def __str__(self):
        return str(self.image_id) + "_" + str(self.label)


@admin.register(ImageAnnotation)
class ImageAnnotationAdmin(admin.ModelAdmin):
    list_display = (
        "image_id",
        "label",
        "label_correctness",
        "image_correctness",
        "created_at",
        "updated_at",
    )


class BankAccount(AbstractBaseModel):
    account_number = models.CharField(max_length=128, blank=False, null=False)
    bank_code = models.CharField(max_length=128, null=True, blank=True)
    account_name = models.CharField(max_length=128, null=False, blank=False)

    def __str__(self):
        return str(self.account_name)


class Transaction(AbstractBaseModel):
    date_of_submission = models.DateTimeField(null=True, blank=True)
    date_of_transaction = models.DateTimeField(null=False, blank=False)

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
