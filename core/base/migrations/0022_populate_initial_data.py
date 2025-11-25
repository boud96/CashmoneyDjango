from django.db import migrations
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta


def create_initial_data(apps, schema_editor):
    Category = apps.get_model("base", "Category")
    Subcategory = apps.get_model("base", "Subcategory")
    BankAccount = apps.get_model("base", "BankAccount")
    CSVMapping = apps.get_model("base", "CSVMapping")
    User = apps.get_model("auth", "User")
    Tag = apps.get_model("base", "Tag")
    Transaction = apps.get_model("base", "Transaction")
    TransactionTag = apps.get_model("base", "TransactionTag")

    # 1. Create Superuser
    if not User.objects.filter(username="admin").exists():
        User.objects.create(
            username="admin",
            email="",
            password=make_password("admin"),
            is_superuser=True,
            is_staff=True
        )
        print("Created default Superuser: admin")

    # 2. Create Default Bank Account
    main_account, _ = BankAccount.objects.get_or_create(
        account_name="Default bank account to be deleted / modified",
        defaults={"account_number": "0000000000", "owners": 1}
    )

    # 3. Create Categories
    initial_categories = {
        "Food": ["Groceries", "Restaurants"],
        "Travel": ["Public transport", "Gas", "Car maintenance", "Parking"],
        "Subscriptions": ["Cloud services", "Internet provider"],
        "Investment": ["Traditional", "Crypto"],
        "Income": ["Job", "Other income"],
        "Other": ["Unknown"]
    }

    subcat_lookup = {}
    for cat_name, subcats in initial_categories.items():
        category, _ = Category.objects.get_or_create(
            name=cat_name,
            defaults={"description": "Default category to be deleted / modified"}
        )
        for sub_name in subcats:
            sub, _ = Subcategory.objects.get_or_create(
                name=sub_name,
                category=category,
                defaults={"description": "Default subcategory to be deleted / modified"}
            )
            subcat_lookup[sub_name] = sub

    # 4. Create Tags
    tag_names = ["Holiday", "Example Data"]
    tag_lookup = {}

    for name in tag_names:
        tag_obj, _ = Tag.objects.get_or_create(name=name)
        tag_lookup[name] = tag_obj

    # 5. Create Transactions
    if not Transaction.objects.exists():
        today = timezone.now()

        # Transaction A: Income (Job)
        txn_a = Transaction.objects.create(
            date_of_transaction=today - timedelta(days=15),
            amount=3000.00,
            currency="USD",
            bank_account=main_account,
            subcategory=subcat_lookup.get("Job"),
            counterparty_name="Tech Corp Inc.",
            transaction_type="Incoming",
            my_note="Monthly Salary",
            want_need_investment="other"
        )

        # Transaction B: Expense (Groceries - Need)
        txn_b = Transaction.objects.create(
            date_of_transaction=today - timedelta(days=5),
            amount=-150.50,
            currency="USD",
            bank_account=main_account,
            subcategory=subcat_lookup.get("Groceries"),
            counterparty_name="Supermarket",
            transaction_type="Card Payment",
            want_need_investment="need"
        )

        # Transaction C: Expense (Gas - Need)
        txn_c = Transaction.objects.create(
            date_of_transaction=today - timedelta(days=3),
            amount=-60.00,
            currency="USD",
            bank_account=main_account,
            subcategory=subcat_lookup.get("Gas"),
            counterparty_name="Shell Station",
            transaction_type="Card Payment",
            want_need_investment="need"
        )

        # Transaction D: Expense (Restaurants - Want) + Tagged as "Holiday"
        txn_d = Transaction.objects.create(
            date_of_transaction=today - timedelta(days=1),
            amount=-85.00,
            currency="USD",
            bank_account=main_account,
            subcategory=subcat_lookup.get("Restaurants"),
            counterparty_name="Italian Bistro",
            transaction_type="Card Payment",
            my_note="Dinner while on vacation",
            want_need_investment="want"
        )

        # Link the specific Holiday tag
        TransactionTag.objects.create(transaction=txn_d, tag=tag_lookup["Holiday"])

        # Link the "Example Data" tag to ALL transactions
        example_tag = tag_lookup["Example Data"]
        for txn in [txn_a, txn_b, txn_c, txn_d]:
            TransactionTag.objects.create(transaction=txn, tag=example_tag)

        print("Created sample transactions and tags.")

    # 6. Create CSV Mapping
    if not CSVMapping.objects.exists():
        CSVMapping.objects.create(
            name="Default Generic Import to be deleted / modified",
            encoding="utf-8",
            delimiter=";",
            header=0,
            date_of_transaction_value="Date",
            date_of_transaction_format="%d.%m.%Y",
            amount="Amount",
            currency="Currency",
            counterparty_name="Name",
            my_note="Note",
            variable_symbol="VS",
        )


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0021_alter_keyword_rules"),
    ]

    operations = [
        migrations.RunPython(create_initial_data, reverse_func),
    ]