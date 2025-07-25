# Generated by Django 5.0.2 on 2025-07-13 09:42

import multiselectfield.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0019_delete_currencyconversionrate_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="keyword",
            name="rules",
            field=models.JSONField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name="csvmapping",
            name="categorization_fields",
            field=multiselectfield.db.fields.MultiSelectField(
                blank=True,
                choices=[
                    ("my_note", "My Note"),
                    ("other_note", "Other Note"),
                    ("counterparty_note", "Counterparty Note"),
                    ("counterparty_name", "Counterparty Name"),
                    ("counterparty_account_number", "Counterparty Account Number"),
                    ("transaction_type", "Transaction Type"),
                    ("variable_symbol", "Variable Symbol"),
                    ("specific_symbol", "Specific Symbol"),
                    ("constant_symbol", "Constant Symbol"),
                ],
                help_text="Select fields you want to use for categorization.",
                max_length=147,
            ),
        ),
    ]
