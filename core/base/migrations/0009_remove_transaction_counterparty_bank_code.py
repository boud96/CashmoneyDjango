# Generated by Django 5.0.2 on 2024-12-30 17:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0008_csvmapping"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transaction",
            name="counterparty_bank_code",
        ),
    ]