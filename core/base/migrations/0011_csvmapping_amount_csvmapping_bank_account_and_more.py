# Generated by Django 5.0.2 on 2025-01-05 09:32

import core.base.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0010_remove_bankaccount_bank_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="csvmapping",
            name="amount",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="bank_account",
            field=models.ForeignKey(
                default=core.base.models.get_default_bank_account,
                on_delete=django.db.models.deletion.CASCADE,
                to="base.bankaccount",
            ),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="constant_symbol",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="counterparty_account_number",
            field=models.CharField(
                blank=True,
                help_text="Can be account number with or without bank code.",
                max_length=128,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="counterparty_bank_code",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="counterparty_name",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="counterparty_note",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="currency",
            field=models.CharField(blank=True, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="date_of_submission_format",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="date_of_submission_value",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="date_of_transaction_format",
            field=models.CharField(default="%d.%m.%Y", max_length=128),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="date_of_transaction_value",
            field=models.CharField(default="PLACEHOLDER", max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="delimiter",
            field=models.CharField(default=",", max_length=5),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="encoding",
            field=models.CharField(default="utf-8", max_length=128),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="header",
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="my_note",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="original_id",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="other_note",
            field=models.TextField(
                blank=True,
                help_text="Store a list of notes as a comma-separated string.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="specific_symbol",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="transaction_type",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="csvmapping",
            name="variable_symbol",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
