# Generated by Django 5.0.2 on 2024-11-17 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0005_keyword"),
    ]

    operations = [
        migrations.AddField(
            model_name="keyword",
            name="wni",
            field=models.CharField(
                blank=True,
                choices=[
                    ("want", "Want"),
                    ("investment", "Investment"),
                    ("need", "Need"),
                    ("other", "Other"),
                ],
                max_length=128,
                null=True,
            ),
        ),
    ]