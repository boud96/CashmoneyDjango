import io
import json
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

import pandas as pd

from django.core.files.uploadedfile import UploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.db import IntegrityError
from django.db.models import QuerySet
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import (
    CSVMapping,
    Transaction,
    BankAccount,
    Keyword,
    Subcategory,
    Category,
    Tag,
)


@dataclass
class CategorizationResult:
    subcategory: Optional[object] = None
    want_need_investment: Optional[str] = None
    ignore: bool = False
    is_category_overlap: bool = False
    is_uncategorized: bool = False

    def to_dict(self):
        return {
            "subcategory": self.subcategory,
            "want_need_investment": self.want_need_investment,
            "ignore": self.ignore,
        }


class TransactionImporter:
    def __init__(
        self, csv_map: CSVMapping, bank_account: BankAccount, file: UploadedFile
    ):
        self.csv_map = csv_map
        self.bank_account = bank_account
        self.file = file

        # Output lists
        self.created = []
        self.already_imported = []
        self.possible_duplicates = []
        self.category_overlaps = []
        self.uncategorized = []
        self.errors = []

    def run(self) -> dict:
        """Main execution method."""
        try:
            df = self._prepare_df()
        except Exception as e:
            return {"error": f"Failed to parse CSV: {str(e)}"}

        self.keywords = list(Keyword.objects.all().order_by("description"))

        for index, row in df.iterrows():
            try:
                self._process_row(row)
            except Exception as e:
                self.errors.append(
                    {"index": index, "error": str(e), "row_data": row.to_dict()}
                )

        Transaction.objects.bulk_create(self.created)

        return self._generate_report(len(df))

    def _prepare_df(self) -> pd.DataFrame:
        raw_data = self.file.read().decode(self.csv_map.encoding)
        cleaned_data = "\n".join(
            line.rstrip(self.csv_map.delimiter) for line in raw_data.splitlines()
        )

        df = pd.read_csv(
            io.StringIO(cleaned_data),
            encoding=self.csv_map.encoding,
            header=self.csv_map.header,
            delimiter=self.csv_map.delimiter,
            on_bad_lines="warn",
            dtype=str,
        ).fillna("")

        # Clean whitespace
        df.columns = df.columns.str.replace(r"\xa0", " ", regex=True)
        df = df.map(
            lambda x: x.replace(r"\xa0", " ").strip() if isinstance(x, str) else x
        )

        return df

    def _process_row(self, row: pd.Series):
        # 1. Extract Basic Data
        data = self._extract_model_data(row)

        # 2. Add raw_data
        data["raw_data"] = row.to_dict()

        # 3. Categorization
        cat_string = self._create_categorization_string(data)
        cat_result = self._apply_categorization(cat_string, data)

        data.update(cat_result.to_dict())

        # 4. Create Instance
        model_fields = {f.name for f in Transaction._meta.get_fields()}
        clean_data = {k: v for k, v in data.items() if k in model_fields}

        transaction = Transaction(**clean_data)

        # 5. Duplicate Detection
        if self._is_duplicate(transaction):
            return

        # 6. Collect stats
        if cat_result.is_category_overlap:
            self.category_overlaps.append(transaction)
        if cat_result.is_uncategorized:
            self.uncategorized.append(model_to_dict(transaction))

        self.created.append(transaction)

    def _extract_model_data(self, row: pd.Series) -> Dict[str, Any]:
        """Extracts mapped columns into a dictionary matching Transaction model fields."""
        map = self.csv_map

        # Parse Amount
        amount_val = row.get(map.amount, "0")
        if isinstance(amount_val, str):
            amount_val = amount_val.replace(",", ".").replace(" ", "")
        amount = float(amount_val) if amount_val else 0.0

        # Parse Dates
        dos_val = row.get(map.date_of_submission_value)
        date_submission = (
            datetime.strptime(dos_val, map.date_of_submission_format)
            if dos_val
            else None
        )

        dot_val = row.get(map.date_of_transaction_value)
        if not dot_val:
            raise ValueError("Date of transaction is missing")
        date_transaction = datetime.strptime(dot_val, map.date_of_transaction_format)

        # Parse Accounts
        acc_num = row.get(map.counterparty_account_number, "").strip()
        bank_code = row.get(map.counterparty_bank_code, "").strip()

        if acc_num and bank_code:
            cp_account = f"{acc_num}/{bank_code}"
        elif bank_code:
            cp_account = bank_code
        else:
            cp_account = acc_num

        # Other notes logic
        other_note_cols = map.get_other_note_list()
        other_note = " ".join(str(row.get(col, "")) for col in other_note_cols).strip()

        return {
            "original_id": row.get(map.original_id),
            "date_of_submission": date_submission,
            "date_of_transaction": date_transaction,
            "amount": amount,
            "currency": row.get(
                map.currency, "CZK"
            ),  # Default to CZK TODO: Fetch default from settings when implemented
            "bank_account": self.bank_account,
            "my_note": row.get(map.my_note),
            "other_note": other_note,
            "counterparty_note": row.get(map.counterparty_note),
            "constant_symbol": row.get(map.constant_symbol) or None,
            "specific_symbol": row.get(map.specific_symbol) or None,
            "variable_symbol": row.get(map.variable_symbol) or None,
            "transaction_type": row.get(map.transaction_type),
            "counterparty_account_number": cp_account,
            "counterparty_name": row.get(map.counterparty_name),
        }

    def _create_categorization_string(self, data: dict) -> str:
        parts = []
        for field_name in self.csv_map.categorization_fields:
            val = data.get(field_name)
            if val:
                parts.append(str(val))
        return " | ".join(parts)

    def _apply_categorization(
        self, cat_string: str, data: dict
    ) -> CategorizationResult:
        cat_string = cat_string.lower().replace(" ", "")
        result = CategorizationResult()

        # Hard check for own account transfer
        if BankAccount.objects.filter(
            account_number=data.get("counterparty_account_number")
        ).exists():
            result.ignore = True
            return result

        matched = []

        for keyword in self.keywords:

            def check_rules(rules):
                norm_rules = [r.lower().replace(" ", "") for r in rules]
                return all(r in cat_string for r in norm_rules)

            include = check_rules(keyword.rules.get("include", []))
            exclude = False
            if include:
                exclude = any(
                    r.lower().replace(" ", "") in cat_string
                    for r in keyword.rules.get("exclude", [])
                )

            if include and not exclude:
                matched.append(keyword)

        if not matched:
            result.is_uncategorized = True
            return result

        if len(matched) == 1:
            k = matched[0]
            result.subcategory = k.subcategory
            result.want_need_investment = k.want_need_investment
            result.ignore = k.ignore
            return result

        first = matched[0]
        all_same = all(
            m.subcategory == first.subcategory
            and m.want_need_investment == first.want_need_investment
            and m.ignore == first.ignore
            for m in matched
        )

        if all_same:
            result.subcategory = first.subcategory
            result.want_need_investment = first.want_need_investment
            result.ignore = first.ignore
        else:
            result.is_category_overlap = True

        return result

    def _is_duplicate(self, transaction: Transaction) -> bool:
        """
        Checks logic for duplicates and appends to internal lists.
        Returns True if it is a duplicate/skipped, False if it should be created.
        """
        if transaction.original_id:
            exists = Transaction.objects.filter(
                original_id=transaction.original_id,
                date_of_transaction=transaction.date_of_transaction,
                amount=transaction.amount,
            ).exists()
            if exists:
                self.already_imported.append(transaction)
                return True
        else:
            # Fallback for transactions without IDs (fuzzy match)
            exists = Transaction.objects.filter(
                date_of_transaction=transaction.date_of_transaction,
                amount=transaction.amount,
                counterparty_account_number=transaction.counterparty_account_number,
                variable_symbol=transaction.variable_symbol,
            ).exists()
            if exists:
                self.possible_duplicates.append(transaction)
                return True

        return False

    def _generate_report(self, total_loaded: int) -> dict:
        return {
            "loaded": total_loaded,
            "created": {
                "message": f"Successfully imported {len(self.created)} transactions",
                "count": len(self.created),
                "category_overlap": {
                    "count": len(self.category_overlaps),
                    "transactions": [model_to_dict(t) for t in self.category_overlaps],
                },
                "uncategorized": {
                    "count": len(self.uncategorized),
                    "transactions": self.uncategorized,  # Already dicts
                },
            },
            "skipped": {
                "total": len(self.already_imported)
                + len(self.possible_duplicates)
                + len(self.errors),
                "already_imported": len(self.already_imported),
                "possible_duplicates": {
                    "count": len(self.possible_duplicates),
                    "transactions": [
                        model_to_dict(t) for t in self.possible_duplicates
                    ],
                },
                "errors": {"count": len(self.errors), "details": self.errors},
            },
        }


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


@method_decorator(csrf_exempt, name="dispatch")
class ImportTransactionsView(View):
    def post(self, request):
        csv_map_id = request.POST.get("csv_map_id")
        bank_account_id = request.POST.get("bank_account_id")
        csv_file = request.FILES.get("csv_file")

        if not all([csv_map_id, bank_account_id, csv_file]):
            return HttpResponseBadRequest(
                "Missing required fields: csv_map_id, bank_account_id, or csv_file."
            )

        try:
            csv_map = CSVMapping.objects.get(id=csv_map_id)
            bank_account = BankAccount.objects.get(id=bank_account_id)
        except (CSVMapping.DoesNotExist, BankAccount.DoesNotExist):
            return HttpResponseBadRequest("Invalid CSV Mapping or Bank Account ID.")

        importer = TransactionImporter(csv_map, bank_account, csv_file)
        report = importer.run()

        if "error" in report:
            return JsonResponse(report, status=500)

        return JsonResponse(report, status=201)


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
        name = None
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            name = data.get("name")
            description = data.get("description")

            if not name:
                return JsonResponse({"error": "Name is required"}, status=400)

            category = Category.objects.create(name=name, description=description)

            return JsonResponse(
                {"message": "Category created successfully", "id": category.id},
                status=201,
            )

        except IntegrityError:
            return JsonResponse(
                {"error": f"A category with the name '{name}' already exists."},
                status=409,
            )

        except Exception as e:
            # Catch-all for other unexpected errors
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DeleteCategoriesView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            ids = data.get("ids", [])

            if not ids or not isinstance(ids, list):
                return JsonResponse(
                    {"message": "No valid IDs list provided"}, status=400
                )

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
        name = None
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

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
                return JsonResponse({"error": "Parent Category not found"}, status=404)

            subcategory = Subcategory.objects.create(
                name=name, description=description, category=category
            )

            return JsonResponse(
                {"message": "Subcategory created successfully", "id": subcategory.id},
                status=201,
            )

        except IntegrityError:
            return JsonResponse(
                {"error": f"A subcategory with the name '{name}' already exists."},
                status=409,
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
                return JsonResponse(
                    {"message": "No valid IDs list provided"}, status=400
                )

            count, _ = Subcategory.objects.filter(id__in=ids).delete()

            return JsonResponse(
                {"message": "Subcategories deleted successfully", "count": count},
                status=200,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class CreateBankAccountView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            account_number = data.get("account_number")
            account_name = data.get("account_name")
            owners = data.get("owners", 1)

            if not account_number:
                return JsonResponse({"error": "Account Number is required"}, status=400)
            if not account_name:
                return JsonResponse({"error": "Account Name is required"}, status=400)

            bank_account = BankAccount.objects.create(
                account_number=account_number, account_name=account_name, owners=owners
            )

            return JsonResponse(
                {"message": "Bank Account created successfully", "id": bank_account.id},
                status=201,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DeleteBankAccountsView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])

            if not ids or not isinstance(ids, list):
                return JsonResponse({"message": "No valid IDs provided"}, status=200)

            count, _ = BankAccount.objects.filter(id__in=ids).delete()

            return JsonResponse(
                {"message": "Bank Accounts deleted successfully", "count": count},
                status=200,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class CreateCSVMappingView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)

            name = data.get("name")
            date_of_transaction_value = data.get("date_of_transaction_value")

            if not name:
                return JsonResponse({"error": "Name is required"}, status=400)
            if not date_of_transaction_value:
                return JsonResponse(
                    {"error": "Date of Transaction Column is required"}, status=400
                )

            other_note_list = data.get("other_note", [])
            other_note_str = (
                ",".join(other_note_list) if isinstance(other_note_list, list) else ""
            )

            categorization_fields = data.get("categorization_fields", [])

            mapping = CSVMapping.objects.create(
                name=name,
                amount=data.get("amount"),
                header=data.get("header", 0),
                my_note=data.get("my_note"),
                currency=data.get("currency"),
                encoding=data.get("encoding", "utf-8"),
                delimiter=data.get("delimiter", ","),
                other_note=other_note_str,
                original_id=data.get("original_id"),
                constant_symbol=data.get("constant_symbol"),
                specific_symbol=data.get("specific_symbol"),
                variable_symbol=data.get("variable_symbol"),
                transaction_type=data.get("transaction_type"),
                counterparty_name=data.get("counterparty_name"),
                counterparty_note=data.get("counterparty_note"),
                date_of_submission_value=data.get("date_of_submission_value"),
                date_of_submission_format=data.get("date_of_submission_format"),
                date_of_transaction_value=date_of_transaction_value,
                date_of_transaction_format=data.get(
                    "date_of_transaction_format", "%d.%m.%Y"
                ),
                counterparty_account_number=data.get("counterparty_account_number"),
                counterparty_bank_code=data.get("counterparty_bank_code"),
                categorization_fields=categorization_fields,
            )

            return JsonResponse(
                {"message": "CSV Mapping created successfully", "id": mapping.id},
                status=201,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DeleteCSVMappingsView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])

            if not ids or not isinstance(ids, list):
                return JsonResponse({"message": "No valid IDs provided"}, status=200)

            count, _ = CSVMapping.objects.filter(id__in=ids).delete()

            return JsonResponse(
                {"message": "CSV Mappings deleted successfully", "count": count},
                status=200,
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class CreateTagView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            name = data.get("name")
            description = data.get("description")

            if not name:
                return JsonResponse({"error": "Name is required"}, status=400)

            tag = Tag.objects.create(name=name, description=description)

            return JsonResponse(
                {"message": "Tag created successfully", "id": tag.id}, status=201
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DeleteTagsView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])

            if not ids or not isinstance(ids, list):
                return JsonResponse({"message": "No valid IDs provided"}, status=200)

            count, _ = Tag.objects.filter(id__in=ids).delete()

            return JsonResponse(
                {"message": "Tags deleted successfully", "count": count}, status=200
            )
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)
