import io
import traceback
from datetime import datetime
from typing import Optional

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import CSVMapping, Transaction, BankAccount
from ..utils import get_matching_keyword_objs


def get_original_id(row: pd.Series, csv_map: dict) -> str:
    return row.get(csv_map.get("original_id"))


def get_date_of_submission(row: pd.Series, csv_map: dict) -> Optional[datetime]:
    dof_key = csv_map.get("date_of_submission").get("value")
    dof_format = csv_map.get("date_of_submission").get("format")

    dof_value = row.get(dof_key)
    if dof_value:
        return datetime.strptime(dof_value, dof_format)
    return None


def get_date_of_transaction(row: pd.Series, csv_map: dict) -> datetime:
    """
    Get the date of transaction from the row.
    The date of transaction is required, so if it's not found, raise an error.
    """
    dot_key = csv_map.get("date_of_transaction").get("value")
    dot_format = csv_map.get("date_of_transaction").get("format")

    dot_value = row.get(dot_key)
    if not dot_value:
        raise ValueError(f"Value for {dot_key} not found")
    return datetime.strptime(dot_value, dot_format)


def get_amount(row: pd.Series, csv_map: dict) -> float:
    amount = row.get(csv_map.get("amount"))
    if isinstance(amount, str):
        amount = amount.replace(",", ".").replace(" ", "")
    return float(amount)


def get_currency(row: pd.Series, csv_map: dict) -> str:
    currency = row.get(csv_map.get("currency"))
    if not currency:
        currency = "CZK"  # TODO: Model for currency and convert to default currency?
    return currency


def get_bank_account(bank_account_id: str) -> BankAccount:
    return BankAccount.objects.get(id=bank_account_id)


def get_my_note(row: pd.Series, csv_map: dict) -> str:
    return row.get(csv_map.get("my_note"))


def get_other_note(row: pd.Series, csv_map: dict) -> str:
    other_note_columns = csv_map.get("other_note", [])  # Expecting a list of column names
    other_note = " ".join(str(row.get(col, "")) for col in other_note_columns).strip()
    return other_note


def get_counterparty_note(row: pd.Series, csv_map: dict) -> str:
    return row.get(csv_map.get("counterparty_note"))


def get_constant_symbol(row: pd.Series, csv_map: dict) -> str:
    return row.get(csv_map.get("constant_symbol"))


def get_specific_symbol(row: pd.Series, csv_map: dict) -> str:
    return row.get(csv_map.get("specific_symbol"))


def get_variable_symbol(row: pd.Series, csv_map: dict) -> str:
    return row.get(csv_map.get("variable_symbol"))


def get_transaction_type(row: pd.Series, csv_map: dict) -> str:
    return row.get(csv_map.get("transaction_type"))


def get_counterparty_account_number(row: pd.Series, csv_map: dict) -> str:
    """
    Get the counterparty account number from the row.
    If the bank code is provided, return the bank code and account number together.
    Some csv files have the bank code and account number in one column, some in separate columns.
    """
    acc_num = csv_map.get("counterparty_account_number")
    bank_code = csv_map.get("counterparty_bank_code")

    acc_num_value = row.get(acc_num).strip().replace(" ", "")
    bank_code_value = row.get(bank_code).strip().replace(" ", "")

    if not acc_num_value and not bank_code_value:
        return ""
    if not acc_num_value:
        return bank_code_value
    if not bank_code_value:
        return acc_num_value

    return f"{acc_num_value}/{bank_code_value}"


def get_counterparty_name(row, csv_map):
    return row.get(csv_map.get("counterparty_name"))


@csrf_exempt  # TODO: Make this view secure and stuff
def import_transactions(request):
    if request.method == "POST":
        try:
            csv_mapping = CSVMapping.objects.get(id=request.POST.get("id"))
            bank_account_id = request.POST.get("bank_account_id")
            csv_file = request.FILES.get("csv_file")

            csv_map = csv_mapping.mapping_json

            encoding = csv_map.get("encoding")
            header = csv_map.get("header")
            delimiter = csv_map.get("delimiter")

            # Trailing delimiters handle - without it, it sometimes throws an error
            raw_data = csv_file.read().decode(encoding)
            cleaned_data = "\n".join(line.rstrip(delimiter) for line in raw_data.splitlines())

            df = pd.read_csv(
                io.StringIO(cleaned_data),
                encoding=encoding,
                header=header,
                delimiter=delimiter,
                on_bad_lines="warn",
                dtype=str
            ).fillna('')

            # Clean up unwanted whitespaces
            df.columns = df.columns.str.replace(r'\xa0', ' ', regex=True)
            df = df.map(lambda x: x.replace(r'\xa0', ' ') if isinstance(x, str) else x)

            # Import data into the Transaction model
            created = []
            duplicates = []
            category_overlap = []
            uncategorized = []
            for index, row in df.iterrows():
                # TODO: Might rework the CSVMap model to have fields instead of one JSON

                # TODO: If row fails, notify on frontend

                original_id = get_original_id(row, csv_map)
                date_of_submission = get_date_of_submission(row, csv_map)
                date_of_transaction = get_date_of_transaction(row, csv_map)
                amount = get_amount(row, csv_map)
                currency = get_currency(row, csv_map)
                bank_account = get_bank_account(bank_account_id)
                my_note = get_my_note(row, csv_map)
                other_note = get_other_note(row, csv_map)
                counterparty_note = get_counterparty_note(row, csv_map)
                constant_symbol = get_constant_symbol(row, csv_map)
                specific_symbol = get_specific_symbol(row, csv_map)
                variable_symbol = get_variable_symbol(row, csv_map)
                transaction_type = get_transaction_type(row, csv_map)
                counterparty_account_number = get_counterparty_account_number(row, csv_map)
                counterparty_name = get_counterparty_name(row, csv_map)

                subcategory = None
                want_need_investment = None
                lookup_str = f"{my_note} {other_note} {counterparty_note} {counterparty_name}"
                matching_keywords = get_matching_keyword_objs(lookup_str)

                is_category_overlap = False
                is_uncategorized = False
                if len(matching_keywords) == 1:
                    subcategory = matching_keywords[0].subcategory
                    want_need_investment = matching_keywords[0].want_need_investment
                elif len(matching_keywords) > 1:
                    is_category_overlap = True
                else:
                    is_uncategorized = True

                ignore = False
                if BankAccount.objects.filter(account_number=counterparty_account_number).exists():
                    ignore = True

                transaction_data = {
                    "original_id": original_id,
                    "date_of_submission": date_of_submission,
                    "date_of_transaction": date_of_transaction,
                    "amount": amount,
                    "currency": currency,
                    "bank_account": bank_account,
                    "my_note": my_note,
                    "other_note": other_note,
                    "counterparty_note": counterparty_note,
                    "constant_symbol": constant_symbol,
                    "specific_symbol": specific_symbol,
                    "variable_symbol": variable_symbol,
                    "transaction_type": transaction_type,
                    "counterparty_account_number": counterparty_account_number,
                    "counterparty_name": counterparty_name,
                    "subcategory": subcategory,
                    "want_need_investment": want_need_investment,
                    "ignore": ignore
                }

                transaction = Transaction(**transaction_data)
                duplicate_exists = Transaction.objects.filter(
                    original_id=transaction.original_id,
                    date_of_transaction=transaction.date_of_transaction,
                    date_of_submission=transaction.date_of_submission,
                    amount=transaction.amount,
                    currency=transaction.currency,
                    bank_account=transaction.bank_account,
                ).exists()

                if duplicate_exists:
                    duplicates.append(str(transaction))
                    continue
                if is_category_overlap:
                    category_overlap.append(str(transaction))
                if is_uncategorized:
                    uncategorized.append(str(transaction))

                created.append(transaction)

            Transaction.objects.bulk_create(created)

            return JsonResponse(
                {
                    "loaded": len(df),
                    "created": {
                        "message": f"Succesfully imported {len(created)} transactions",
                        "transactions": [str(t) for t in created],
                        "category_overlap": {
                            "message": f"Uncategorized {len(category_overlap)} transactions due to category overlap",
                            "transactions": category_overlap
                        },
                        "uncategorized": {
                            "message": f"Uncategorized {len(uncategorized)} transactions due to no matching keywords",
                            "transactions": uncategorized
                        }
                    },
                    "skipped": {
                        "message": f"Skipped {len(duplicates)} transactions due to duplicates",
                        "transactions": duplicates
                    }  # TODO: whole loop into Try-Except, append other reasons to generic skipped
                    # add other skip types if needed
                }
                , status=201)

        except Exception as e:
            print(traceback.format_exc())  # TODO: DEBUG remove
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
