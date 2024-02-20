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
