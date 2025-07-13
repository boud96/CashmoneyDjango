import io
import traceback
from datetime import datetime
from typing import Optional

import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.forms import model_to_dict
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import CSVMapping, Transaction, BankAccount
from core.base.utils.utils import get_matching_keyword_objs


def get_original_id(row: pd.Series, csv_map: CSVMapping) -> str:
    return row.get(csv_map.original_id)


def get_date_of_submission(row: pd.Series, csv_map: CSVMapping) -> Optional[datetime]:
    dos_row_value = row.get(csv_map.date_of_submission_value)
    if dos_row_value:
        return datetime.strptime(dos_row_value, csv_map.date_of_submission_format)
    return None


def get_date_of_transaction(row: pd.Series, csv_map: CSVMapping) -> datetime:
    """
    Get the date of transaction from the row.
    The date of transaction is required, so if it's not found, raise an error.
    """
    dot_row_value = row.get(csv_map.date_of_transaction_value)
    if not dot_row_value:
        raise ValueError(f"Value for {dot_row_value} not found")
    return datetime.strptime(dot_row_value, csv_map.date_of_transaction_format)


def get_amount(row: pd.Series, csv_map: CSVMapping) -> float:
    amount = row.get(csv_map.amount)
    if isinstance(amount, str):
        amount = amount.replace(",", ".").replace(" ", "")
    return float(amount)  # TODO: Handle missing amount (add transaction to skipped?)


def get_currency(row: pd.Series, csv_map: CSVMapping) -> str:
    currency = row.get(csv_map.currency)
    if not currency:
        currency = "CZK"  # TODO: Model for currency and convert to default currency?
    return currency


def get_bank_account(bank_account_id: str) -> BankAccount:
    return BankAccount.objects.get(id=bank_account_id)


def get_my_note(row: pd.Series, csv_map: CSVMapping) -> str:
    return row.get(csv_map.my_note)


def get_other_note(row: pd.Series, csv_map: CSVMapping) -> str:
    other_note_columns = csv_map.get_other_note_list()
    other_note = " ".join(str(row.get(col, "")) for col in other_note_columns).strip()
    return other_note


def get_counterparty_note(row: pd.Series, csv_map: CSVMapping) -> str:
    return row.get(csv_map.counterparty_note)


def get_constant_symbol(row: pd.Series, csv_map: CSVMapping) -> str:
    return (
        row.get(csv_map.constant_symbol) if row.get(csv_map.constant_symbol) else None
    )


def get_specific_symbol(row: pd.Series, csv_map: CSVMapping) -> str | None:
    return (
        row.get(csv_map.specific_symbol) if row.get(csv_map.specific_symbol) else None
    )


def get_variable_symbol(row: pd.Series, csv_map: CSVMapping) -> str | None:
    return (
        row.get(csv_map.variable_symbol) if row.get(csv_map.variable_symbol) else None
    )


def get_transaction_type(row: pd.Series, csv_map: CSVMapping) -> str:
    return row.get(csv_map.transaction_type)


def get_counterparty_account_number_with_bank_code(
    row: pd.Series, csv_map: CSVMapping
) -> str:
    """
    Get the counterparty account number from the row.
    If the bank code is provided, return the bank code and account number together.
    Some csv files have the bank code and account number in one column, some in separate columns.
    """
    acc_num = csv_map.counterparty_account_number
    bank_code = csv_map.counterparty_bank_code

    acc_num_value = row.get(acc_num).strip().replace(" ", "") if acc_num else None
    bank_code_value = row.get(bank_code).strip().replace(" ", "") if bank_code else None

    if not acc_num_value and not bank_code_value:
        return ""
    if not acc_num_value:
        return bank_code_value
    if not bank_code_value:
        return acc_num_value

    return f"{acc_num_value}/{bank_code_value}"


def get_counterparty_name(row, csv_map: CSVMapping) -> str:
    return row.get(csv_map.counterparty_name)


def create_categorization_string(transaction_data: dict, csv_map: CSVMapping):
    categorization_parts = []
    for field_name in csv_map.categorization_fields:
        value = transaction_data.get(field_name)
        if value:
            categorization_parts.append(str(value))

    categorization_string = " | ".join(categorization_parts)

    return categorization_string


@method_decorator(csrf_exempt, name="dispatch")  # TODO: Make this view secure and stuff
class ImportTransactionsView(View):
    def _prapare_df(
        self, csv_map: CSVMapping, csv_file: InMemoryUploadedFile
    ) -> pd.DataFrame:
        # Trailing delimiters handle - without it, it sometimes throws an error
        raw_data = csv_file.read().decode(csv_map.encoding)
        cleaned_data = "\n".join(
            line.rstrip(csv_map.delimiter) for line in raw_data.splitlines()
        )

        df = pd.read_csv(
            io.StringIO(cleaned_data),
            encoding=csv_map.encoding,
            header=csv_map.header,
            delimiter=csv_map.delimiter,
            on_bad_lines="warn",
            dtype=str,
        ).fillna("")

        # Clean up unwanted whitespaces
        df.columns = df.columns.str.replace(r"\xa0", " ", regex=True)
        df = df.map(lambda x: x.replace(r"\xa0", " ") if isinstance(x, str) else x)

        return df

    def _prepare_transaction_dict(
        self, row: pd.Series, csv_map: CSVMapping, bank_account_id: str
    ) -> dict:
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
        counterparty_account_number = get_counterparty_account_number_with_bank_code(
            row, csv_map
        )
        counterparty_name = get_counterparty_name(row, csv_map)

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
        }

        return transaction_data

    def post(self, request):
        try:
            csv_map = CSVMapping.objects.get(id=request.POST.get("id"))
            bank_account_id = request.POST.get("bank_account_id")
            csv_file = request.FILES.get("csv_file")

            df = self._prapare_df(csv_map, csv_file)

            # Import data into the Transaction model
            created = []
            already_imported = []  # Based on original_id
            possible_duplicates = []  # No original_id but seems to be the same transaction
            category_overlap = []
            uncategorized = []
            for index, row in df.iterrows():
                # TODO: If row fails, notify on frontend
                transaction_data = self._prepare_transaction_dict(
                    row, csv_map, bank_account_id
                )

                # TODO: Rework the Keyword model to use json with "include" and "exclude".
                #  if all strings in "include" pass and no strings in "exclude"
                #  pass the Keyword is assigned
                categorization_string = create_categorization_string(
                    transaction_data, csv_map
                )
                matching_keywords = get_matching_keyword_objs(categorization_string)

                subcategory = None
                want_need_investment = None

                is_category_overlap = False
                is_uncategorized = False
                if len(matching_keywords) == 1:
                    subcategory = matching_keywords[0].subcategory
                    want_need_investment = matching_keywords[0].want_need_investment
                elif len(matching_keywords) > 1:
                    for i in matching_keywords:
                        if (
                            i.subcategory != matching_keywords[0].subcategory
                            or i.want_need_investment
                            != matching_keywords[0].want_need_investment
                        ):  # If all matched keywords have the same subcategories and wni, it's not really an overlap
                            is_category_overlap = True
                            break

                    if not is_category_overlap:
                        subcategory = matching_keywords[0].subcategory
                        want_need_investment = matching_keywords[0].want_need_investment
                else:
                    is_uncategorized = True

                ignore = matching_keywords[0].ignore if matching_keywords else False
                if BankAccount.objects.filter(
                    account_number=transaction_data.get("counterparty_account_number")
                ).exists():
                    ignore = True

                transaction_data.update(
                    {
                        "subcategory": subcategory,
                        "want_need_investment": want_need_investment,
                        "ignore": ignore,
                    }
                )

                # Replace each value that is "" with None
                transaction_data = {
                    k: v if v != "" else None for k, v in transaction_data.items()
                }

                transaction = Transaction(**transaction_data)

                original_id = transaction_data.get("original_id")
                if original_id:
                    duplicate_exists = Transaction.objects.filter(
                        original_id=transaction.original_id,
                        date_of_transaction=transaction.date_of_transaction,
                        amount=transaction.amount,
                    ).exists()
                else:
                    duplicate_exists = Transaction.objects.filter(
                        date_of_transaction=transaction.date_of_transaction,
                        amount=transaction.amount,
                        counterparty_account_number=transaction.counterparty_account_number,
                        currency=transaction.currency,
                        variable_symbol=transaction.variable_symbol,
                        specific_symbol=transaction.specific_symbol,
                        constant_symbol=transaction.constant_symbol,
                    ).exists()

                if duplicate_exists:
                    if original_id:
                        already_imported.append(transaction)
                        continue
                    possible_duplicates.append(transaction)
                    continue

                if is_category_overlap:
                    category_overlap.append(transaction)
                if is_uncategorized:
                    uncategorized.append(str(transaction))

                created.append(transaction)

            Transaction.objects.bulk_create(created)
            crated_transaction_ids = [transaction.pk for transaction in created]
            already_imported_ids = [transaction.pk for transaction in already_imported]
            possible_duplicates_dict_list = [
                model_to_dict(transaction) for transaction in possible_duplicates
            ]
            category_overlap_dict_list = [
                model_to_dict(transaction) for transaction in category_overlap
            ]

            return JsonResponse(
                {
                    "loaded": len(df),
                    "created": {
                        "message": f"Succesfully imported {len(created)} transactions",
                        "transactions": crated_transaction_ids,
                        "category_overlap": {
                            "message": f"Uncategorized {len(category_overlap)} transactions due to category overlap",
                            "transactions": category_overlap_dict_list,
                        },
                        "uncategorized": {
                            "message": f"Uncategorized {len(uncategorized)} transactions due to no matching keywords",
                            "transactions": uncategorized,
                        },
                    },
                    "skipped": {
                        "message": f"Skipped {len(already_imported) + len(possible_duplicates)} transactions",
                        "already_imported": {
                            "message": f"Skipped {len(already_imported)} transactions due to duplicates",
                            "transactions": already_imported_ids,
                        },
                        "possible_duplicates": {
                            "message": f"Skipped {len(possible_duplicates)} possible duplicates without the original transaction ID. Check manually",
                            "transactions": possible_duplicates_dict_list,
                        },
                        "errors": {
                            "message": "Skipped __TODO__ transactions due to errors",
                            # TODO: Retrieve all errors to display, don't forget to add to the skipped message
                        },
                    },  # TODO: whole loop into Try-Except, append other reasons to generic skipped
                    # add other skip types if needed
                },
                status=201,
            )

        except Exception as e:
            print(traceback.format_exc())  # TODO: DEBUG remove
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt  # TODO: Secure this view appropriately
def recategorize_transactions(request):  # TODO: Currently USELESS. Rewrite ASAP
    if request.method == "POST":
        try:
            recategorize_assigned = (
                request.POST.get("recategorize_assigned", "false").lower() == "true"
            )

            if recategorize_assigned:
                transactions = Transaction.objects.all()
            else:
                transactions = Transaction.objects.filter(subcategory__isnull=True)

            updated_transactions = []
            category_overlap = []
            uncategorized = []

            for transaction in transactions:
                # TODO: Implement recatoegorization by CVSMapping fields like in the import
                lookup_str = f"{transaction.my_note}{transaction.other_note}{transaction.counterparty_note}{transaction.counterparty_name}{transaction.counterparty_account_number}"
                matching_keywords = get_matching_keyword_objs(lookup_str)

                subcategory = None
                want_need_investment = None

                is_category_overlap = False
                if len(matching_keywords) == 1:
                    subcategory = matching_keywords[0].subcategory
                    want_need_investment = matching_keywords[0].want_need_investment
                    updated_transactions.append(transaction)

                elif (
                    len(matching_keywords) > 1
                ):  # TODO: Implement this to the import_transactions view
                    first_subcategory = matching_keywords[0].subcategory
                    first_want_need_investment = matching_keywords[
                        0
                    ].want_need_investment
                    all_same = True
                    for keyword in matching_keywords:
                        if (
                            keyword.subcategory != first_subcategory
                            or keyword.want_need_investment
                            != first_want_need_investment
                        ):
                            all_same = False
                            break
                    if all_same:
                        subcategory = first_subcategory
                        want_need_investment = first_want_need_investment
                    else:
                        is_category_overlap = True

                else:
                    uncategorized.append(str(transaction))
                    continue

                if is_category_overlap:
                    category_overlap.append(str(transaction))
                    continue

                # TODO: check if behavior is correct
                ignore = matching_keywords[0].ignore if matching_keywords else False
                if BankAccount.objects.filter(
                    account_number=transaction.counterparty_account_number
                ).exists():
                    ignore = True

                transaction.subcategory = subcategory
                transaction.want_need_investment = want_need_investment
                transaction.ignore = ignore

                updated_transactions.append(transaction)

            Transaction.objects.bulk_update(
                updated_transactions,
                fields=["subcategory", "want_need_investment", "ignore"],
            )

            return JsonResponse(
                {
                    "loaded": {
                        "message": f"Loaded {len(transactions)} transactions",
                        "transactions": [str(t) for t in updated_transactions],
                    },
                    "updated": {
                        "message": f"Updated {len(updated_transactions)} transactions",
                        "transactions": [str(t) for t in updated_transactions],
                    },
                    "skipped": {
                        "message": f"Skipped {len(category_overlap) + len(uncategorized)} transactions",
                        "category_overlap": {
                            "message": f"Overlapping categories for {len(category_overlap)} transactions",
                            "transactions": category_overlap,
                        },
                        "uncategorized": {
                            "message": f"Category not found for {len(uncategorized)} transactions",
                            "transactions": uncategorized,
                        },
                    },
                },
                status=200,
            )

        except Exception as e:
            print(traceback.format_exc())  # TODO: DEBUG remove
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
