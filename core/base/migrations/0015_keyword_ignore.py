# Generated by Django 5.0.2 on 2025-01-05 12:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0014_alter_category_options_alter_subcategory_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="keyword",
            name="ignore",
            field=models.BooleanField(default=False),
        ),
    ]
