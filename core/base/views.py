import io
import json
import traceback
from datetime import datetime
from typing import Optional

import pandas as pd
from django.core.files.uploadedfile import UploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.forms import model_to_dict
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import CSVMapping, Transaction, BankAccount, Keyword, Subcategory, Category


class TransactionFieldsConstants:
    """Constants for Transaction model field names"""

    ORIGINAL_ID = "original_id"
    DATE_OF_SUBMISSION = "date_of_submission"
    DATE_OF_TRANSACTION = "date_of_transaction"
    AMOUNT = "amount"
    CURRENCY = "currency"
    BANK_ACCOUNT = "bank_account"
    MY_NOTE = "my_note"
    OTHER_NOTE = "other_note"
    COUNTERPARTY_NOTE = "counterparty_note"
    CONSTANT_SYMBOL = "constant_symbol"
    SPECIFIC_SYMBOL = "specific_symbol"
    VARIABLE_SYMBOL = "variable_symbol"
    TRANSACTION_TYPE = "transaction_type"
    COUNTERPARTY_ACCOUNT_NUMBER = "counterparty_account_number"
    COUNTERPARTY_NAME = "counterparty_name"
    SUBCATEGORY = "subcategory"
    WANT_NEED_INVESTMENT = "want_need_investment"
    IGNORE = "ignore"


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
    @staticmethod
    def _prepare_df(csv_map: CSVMapping, csv_file: UploadedFile) -> pd.DataFrame:
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

    @staticmethod
    def _prepare_transaction_dict(
        row: pd.Series, csv_map: CSVMapping, bank_account_id: str
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
            TransactionFieldsConstants.ORIGINAL_ID: original_id,
            TransactionFieldsConstants.DATE_OF_SUBMISSION: date_of_submission,
            TransactionFieldsConstants.DATE_OF_TRANSACTION: date_of_transaction,
            TransactionFieldsConstants.AMOUNT: amount,
            TransactionFieldsConstants.CURRENCY: currency,
            TransactionFieldsConstants.BANK_ACCOUNT: bank_account,
            TransactionFieldsConstants.MY_NOTE: my_note,
            TransactionFieldsConstants.OTHER_NOTE: other_note,
            TransactionFieldsConstants.COUNTERPARTY_NOTE: counterparty_note,
            TransactionFieldsConstants.CONSTANT_SYMBOL: constant_symbol,
            TransactionFieldsConstants.SPECIFIC_SYMBOL: specific_symbol,
            TransactionFieldsConstants.VARIABLE_SYMBOL: variable_symbol,
            TransactionFieldsConstants.TRANSACTION_TYPE: transaction_type,
            TransactionFieldsConstants.COUNTERPARTY_ACCOUNT_NUMBER: counterparty_account_number,
            TransactionFieldsConstants.COUNTERPARTY_NAME: counterparty_name,
        }

        return transaction_data

    def _get_matching_keyword_objs(
        self, categorization_string: str
    ) -> QuerySet[Keyword]:
        categorization_string = categorization_string.lower().replace(" ", "")

        include_keywords = Keyword.objects.none()
        exclude_keywords = Keyword.objects.none()
        matching_keywords = Keyword.objects.none()

        for keyword in Keyword.objects.all().order_by("description"):
            all_include_rules = []
            for include_rule in keyword.rules.get("include"):
                all_include_rules.append(include_rule.lower().replace(" ", ""))

            all_exclude_rules = []
            for exclude_rule in keyword.rules.get("exclude"):
                all_exclude_rules.append(exclude_rule.lower().replace(" ", ""))

            if all(
                include_rule in categorization_string
                for include_rule in all_include_rules
            ):
                include_keywords = include_keywords | Keyword.objects.filter(
                    id=keyword.id
                )

            if any(
                exclude_rule in categorization_string
                for exclude_rule in all_exclude_rules
            ):
                exclude_keywords = exclude_keywords | Keyword.objects.filter(
                    id=keyword.id
                )

            matching_keywords = include_keywords.exclude(id__in=exclude_keywords)

        return matching_keywords

    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            csv_map = CSVMapping.objects.get(id=request.POST.get("csv_map_id"))
            bank_account_id = request.POST.get("bank_account_id")
            csv_file = request.FILES.get("csv_file")

            df = self._prepare_df(csv_map, csv_file)

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

                categorization_string = create_categorization_string(
                    transaction_data, csv_map
                )
                matching_keywords = self._get_matching_keyword_objs(
                    categorization_string
                )
                categorization_dict, is_category_overlap, is_uncategorized = (
                    self._create_categorization_dict(
                        matching_keywords, transaction_data
                    )
                )

                transaction_data.update(categorization_dict)

                # Replace each value that is "" with None
                transaction_data = {
                    k: v if v != "" else None for k, v in transaction_data.items()
                }

                transaction = Transaction(**transaction_data)

                original_id = transaction_data.get(
                    TransactionFieldsConstants.ORIGINAL_ID
                )
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

    @staticmethod
    def _create_categorization_dict(
        matching_keywords: QuerySet[Keyword], transaction_data: dict
    ) -> (dict, bool, bool):
        # TODO: Rethink - the 3 returns suck

        subcategory = None
        want_need_investment = None

        is_category_overlap = False
        is_uncategorized = False
        ignore = False

        if len(matching_keywords) == 1:
            subcategory = matching_keywords[0].subcategory
            want_need_investment = matching_keywords[0].want_need_investment
            ignore = matching_keywords[0].ignore if matching_keywords else False

        elif len(matching_keywords) > 1:
            for i in matching_keywords:
                if (
                    # If all matched keywords have the same subcategories, wni and ignore,
                    # just pick the first occurrence since they are the same
                    i.subcategory != matching_keywords[0].subcategory
                    or i.want_need_investment
                    != matching_keywords[0].want_need_investment
                    or i.ignore != matching_keywords[0].ignore
                ):
                    is_category_overlap = True
                    break

            if not is_category_overlap:
                subcategory = matching_keywords[0].subcategory
                want_need_investment = matching_keywords[0].want_need_investment
        else:
            is_uncategorized = True

        if BankAccount.objects.filter(
            account_number=transaction_data.get(
                TransactionFieldsConstants.COUNTERPARTY_ACCOUNT_NUMBER
            )
        ).exists():
            ignore = True

        categorization_dict = {
            TransactionFieldsConstants.SUBCATEGORY: subcategory,
            TransactionFieldsConstants.WANT_NEED_INVESTMENT: want_need_investment,
            TransactionFieldsConstants.IGNORE: ignore,
        }

        return categorization_dict, is_category_overlap, is_uncategorized


@method_decorator(csrf_exempt, name="dispatch")  # TODO: Make this view secure and stuff
class RecategorizeTransactionsView(View):
    """
    View for recategorizing transactions.

    This view loads transactions from the Transaction model and recategorizes them.

    It accepts a list of UUIDs and a list of fields to use for categorization.
    """

    def _create_categorization_string(
        self, transaction: Transaction, fields=None
    ) -> str:
        """
        Create a categorization string from a Transaction object.

        This is similar to the create_categorization_string function but works directly
        with Transaction objects instead of using CSV mappings.  # TODO: Make a Base class for overlapping methods - maybe not this one?

        Args:
            transaction: The Transaction object to create a categorization string from.
            fields: Optional list of fields to use for categorization. Must be a subset of
                   CSVMapping.ALLOWED_FIELDS. If not provided, all ALLOWED_FIELDS are used.
        """

        if fields:
            invalid_fields = [
                field for field in fields if field not in CSVMapping.ALLOWED_FIELDS
            ]
            if invalid_fields:
                raise ValueError(
                    f"Invalid fields: {', '.join(invalid_fields)}. Fields must be in CSVMapping.ALLOWED_FIELDS."
                )

        categorization_parts = []
        for field_name in fields:
            value = getattr(transaction, field_name, None)
            if value:
                categorization_parts.append(str(value))

        categorization_string = " | ".join(categorization_parts)
        return categorization_string

    @staticmethod
    def _get_matching_keyword_objs(categorization_string: str) -> QuerySet[Keyword]:
        """
        Get matching keyword objects for a categorization string.

        This is the same as ImportTransactionsView._get_matching_keyword_objs.  # TODO: Make a Base class for overlapping methods
        """
        categorization_string = categorization_string.lower().replace(" ", "")

        include_keywords = Keyword.objects.none()
        exclude_keywords = Keyword.objects.none()
        matching_keywords = Keyword.objects.none()

        for keyword in Keyword.objects.all().order_by("description"):
            all_include_rules = []
            for include_rule in keyword.rules.get("include"):
                all_include_rules.append(include_rule.lower().replace(" ", ""))

            all_exclude_rules = []
            for exclude_rule in keyword.rules.get("exclude"):
                all_exclude_rules.append(exclude_rule.lower().replace(" ", ""))

            if all(
                include_rule in categorization_string
                for include_rule in all_include_rules
            ):
                include_keywords = include_keywords | Keyword.objects.filter(
                    id=keyword.id
                )

            if any(
                exclude_rule in categorization_string
                for exclude_rule in all_exclude_rules
            ):
                exclude_keywords = exclude_keywords | Keyword.objects.filter(
                    id=keyword.id
                )

            matching_keywords = include_keywords.exclude(id__in=exclude_keywords)

        return matching_keywords

    @staticmethod
    def _create_categorization_dict(
        matching_keywords: QuerySet[Keyword], transaction_data: dict
    ) -> (dict, bool, bool):
        """
        Create a categorization dictionary from matching keywords.

        This is the same as ImportTransactionsView._create_categorization_dict.  # TODO: Make a Base class for overlapping methods
        """
        subcategory = None
        want_need_investment = None

        is_category_overlap = False
        is_uncategorized = False
        ignore = False

        if len(matching_keywords) == 1:
            subcategory = matching_keywords[0].subcategory
            want_need_investment = matching_keywords[0].want_need_investment
            ignore = matching_keywords[0].ignore if matching_keywords else False

        elif len(matching_keywords) > 1:
            for i in matching_keywords:
                if (
                    # If all matched keywords have the same subcategories, wni and ignore,
                    # just pick the first occurrence since they are the same
                    i.subcategory != matching_keywords[0].subcategory
                    or i.want_need_investment
                    != matching_keywords[0].want_need_investment
                    or i.ignore != matching_keywords[0].ignore
                ):
                    is_category_overlap = True
                    break

            if not is_category_overlap:
                subcategory = matching_keywords[0].subcategory
                want_need_investment = matching_keywords[0].want_need_investment
        else:
            is_uncategorized = True

        if BankAccount.objects.filter(
            account_number=transaction_data.get(
                TransactionFieldsConstants.COUNTERPARTY_ACCOUNT_NUMBER
            )
        ).exists():
            ignore = True

        categorization_dict = {
            TransactionFieldsConstants.SUBCATEGORY: subcategory,
            TransactionFieldsConstants.WANT_NEED_INVESTMENT: want_need_investment,
            TransactionFieldsConstants.IGNORE: ignore,
        }

        return categorization_dict, is_category_overlap, is_uncategorized

    def post(self, request: WSGIRequest) -> JsonResponse:
        """
        Handle POST requests to recategorize transactions.
        """
        try:
            uuids = request.POST.getlist("uuids", [])
            fields = request.POST.getlist("fields", [])

            updated = []
            category_overlap = []
            uncategorized = []
            if uuids and fields:
                transactions = Transaction.objects.filter(id__in=uuids)
                for transaction in transactions:
                    transaction_data = {
                        TransactionFieldsConstants.ORIGINAL_ID: transaction.original_id,
                        TransactionFieldsConstants.DATE_OF_SUBMISSION: transaction.date_of_submission,
                        TransactionFieldsConstants.DATE_OF_TRANSACTION: transaction.date_of_transaction,
                        TransactionFieldsConstants.AMOUNT: transaction.amount,
                        TransactionFieldsConstants.CURRENCY: transaction.currency,
                        TransactionFieldsConstants.BANK_ACCOUNT: transaction.bank_account,
                        TransactionFieldsConstants.MY_NOTE: transaction.my_note,
                        TransactionFieldsConstants.OTHER_NOTE: transaction.other_note,
                        TransactionFieldsConstants.COUNTERPARTY_NOTE: transaction.counterparty_note,
                        TransactionFieldsConstants.CONSTANT_SYMBOL: transaction.constant_symbol,
                        TransactionFieldsConstants.SPECIFIC_SYMBOL: transaction.specific_symbol,
                        TransactionFieldsConstants.VARIABLE_SYMBOL: transaction.variable_symbol,
                        TransactionFieldsConstants.TRANSACTION_TYPE: transaction.transaction_type,
                        TransactionFieldsConstants.COUNTERPARTY_ACCOUNT_NUMBER: transaction.counterparty_account_number,
                        TransactionFieldsConstants.COUNTERPARTY_NAME: transaction.counterparty_name,
                    }

                    categorization_string = self._create_categorization_string(
                        transaction, fields
                    )
                    matching_keywords = self._get_matching_keyword_objs(
                        categorization_string
                    )
                    categorization_dict, is_category_overlap, is_uncategorized = (
                        self._create_categorization_dict(
                            matching_keywords, transaction_data
                        )
                    )

                    transaction.subcategory = categorization_dict[
                        TransactionFieldsConstants.SUBCATEGORY
                    ]
                    transaction.want_need_investment = categorization_dict[
                        TransactionFieldsConstants.WANT_NEED_INVESTMENT
                    ]
                    transaction.ignore = categorization_dict[
                        TransactionFieldsConstants.IGNORE
                    ]
                    transaction.save()

                    if is_category_overlap:
                        category_overlap.append(transaction)
                    elif is_uncategorized:
                        uncategorized.append(transaction)
                    else:
                        updated.append(transaction)

            # Create response
            return JsonResponse(
                {
                    "updated": {
                        "message": f"Successfully recategorized {len(updated)} transactions",
                        "transactions": [str(transaction) for transaction in updated],
                    },
                    "category_overlap": {
                        "message": f"Uncategorized {len(category_overlap)} transactions due to category overlap",
                        "transactions": [
                            str(transaction) for transaction in category_overlap
                        ],
                    },
                    "uncategorized": {
                        "message": f"Uncategorized {len(uncategorized)} transactions due to no matching keywords",
                        "transactions": [
                            str(transaction) for transaction in uncategorized
                        ],
                    },
                },
                status=200,
            )

        except Exception as e:
            print(traceback.format_exc())  # TODO: DEBUG remove
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class CreateKeywordView(View):
    """
    View for creating new Keyword objects.
    Accepts a JSON payload defining the keyword properties and rules.
    """

    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON format"}, status=400)

            description = data.get("description")
            subcategory_id = data.get("subcategory")
            wni = data.get("want_need_investment")
            ignore = data.get("ignore", False)
            rules = data.get("rules", {})

            if not description:
                return JsonResponse({"error": "Description is required"}, status=400)
            if not subcategory_id:
                return JsonResponse({"error": "Subcategory ID is required"}, status=400)

            try:
                subcategory = Subcategory.objects.get(id=subcategory_id)
            except Subcategory.DoesNotExist:
                return JsonResponse(
                    {"error": f"Subcategory with id {subcategory_id} does not exist"},
                    status=404,
                )

            keyword = Keyword.objects.create(
                description=description,
                subcategory=subcategory,
                want_need_investment=wni,
                ignore=ignore,
                rules=rules,
            )

            return JsonResponse(
                {
                    "message": "Keyword created successfully",
                    "id": keyword.id,
                    "description": keyword.description,
                    "subcategory": str(keyword.subcategory),
                },
                status=201,
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DeleteKeywordsView(View):
    """
    View for bulk deleting Keyword objects.
    Accepts a JSON payload: {"ids": ["uuid1", "uuid2", ...]}
    """

    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON format"}, status=400)

            ids = data.get("ids", [])

            if not isinstance(ids, list):
                return JsonResponse({"error": "'ids' must be a list"}, status=400)

            if not ids:
                return JsonResponse({"message": "No IDs provided"}, status=200)

            deleted_count, _ = Keyword.objects.filter(id__in=ids).delete()

            return JsonResponse(
                {"message": "Keywords deleted successfully", "count": deleted_count},
                status=200,
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class CreateCategoryView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            name = data.get("name")
            description = data.get("description")

            if not name:
                return JsonResponse({"error": "Name is required"}, status=400)

            category = Category.objects.create(name=name, description=description)

            return JsonResponse(
                {"message": "Category created successfully", "id": category.id},
                status=201,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DeleteCategoriesView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])

            if not ids or not isinstance(ids, list):
                return JsonResponse({"message": "No valid IDs provided"}, status=200)

            count, _ = Category.objects.filter(id__in=ids).delete()

            return JsonResponse(
                {"message": "Categories deleted successfully", "count": count},
                status=200,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class CreateSubcategoryView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            name = data.get("name")
            description = data.get("description")
            category_id = data.get("category_id")

            if not name:
                return JsonResponse({"error": "Name is required"}, status=400)
            if not category_id:
                return JsonResponse({"error": "Category ID is required"}, status=400)

            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return JsonResponse({"error": "Category not found"}, status=404)

            subcategory = Subcategory.objects.create(
                name=name, description=description, category=category
            )

            return JsonResponse(
                {"message": "Subcategory created successfully", "id": subcategory.id},
                status=201,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DeleteSubcategoriesView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])

            if not ids or not isinstance(ids, list):
                return JsonResponse({"message": "No valid IDs provided"}, status=200)

            count, _ = Subcategory.objects.filter(id__in=ids).delete()

            return JsonResponse(
                {"message": "Subcategories deleted successfully", "count": count},
                status=200,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)
