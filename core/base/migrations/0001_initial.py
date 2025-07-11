# Generated by Django 5.0.2 on 2024-02-19 22:11

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ImageAnnotation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("image_id", models.CharField(max_length=60)),
                ("label", models.CharField(max_length=60)),
                ("height", models.IntegerField(default=-1)),
                ("width", models.IntegerField(default=-1)),
                (
                    "label_correctness",
                    models.CharField(
                        choices=[
                            ("KO", "Ko"),
                            ("TO_BE_CHECKED", "To Be Checked"),
                            ("OK", "Ok"),
                        ],
                        default="TO_BE_CHECKED",
                        max_length=24,
                    ),
                ),
                (
                    "image_correctness",
                    models.CharField(
                        choices=[
                            ("KO", "Ko"),
                            ("TO_BE_CHECKED", "To Be Checked"),
                            ("OK", "Ok"),
                        ],
                        default="TO_BE_CHECKED",
                        max_length=24,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
