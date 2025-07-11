# Generated by Django 5.0.2 on 2024-11-09 17:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0002_bankaccount_category_transaction_subcategory"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ImageAnnotation",
        ),
        migrations.AddField(
            model_name="bankaccount",
            name="owners",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="transaction",
            name="bank_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="base.bankaccount",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="subcategory",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="base.subcategory",
            ),
        ),
    ]
