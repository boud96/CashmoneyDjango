import io
import json
from datetime import datetime
from typing import Dict, Any

import pandas as pd

from django.core.files.uploadedfile import UploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.db import IntegrityError
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.base.models import (
    CSVMapping,
    Transaction,
    BankAccount,
    Subcategory,
    Keyword,
    Category,
    Tag,
)
from core.services import CategorizationService


class TransactionImporter:
    def __init__(
        self, csv_map: CSVMapping, bank_account: BankAccount, file: UploadedFile
    ):
        self.csv_map = csv_map
        self.bank_account = bank_account
        self.file = file

        self.cat_service = CategorizationService()
        # Output lists
        self.created = []
        self.already_imported = []
        self.possible_duplicates = []
        self.category_overlaps = []
        self.uncategorized = []
        self.errors = []

    def run(self) -> dict:
        try:
            df = self._prepare_df()
        except Exception as e:
            return {"error": f"Failed to parse CSV: {str(e)}"}

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
        cat_string = self.cat_service.get_categorization_string(data, self.csv_map)
        cat_result = self.cat_service.apply_categorization(cat_string, data)

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

    def _is_duplicate(self, transaction: Transaction) -> bool:
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
                    "transactions": self.uncategorized,
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
        bank_account_id = request.POST.get("bank_account_id")
        csv_file = request.FILES.get("csv_file")

        if not all([bank_account_id, csv_file]):
            return HttpResponseBadRequest(
                "Missing required fields: bank_account_id or csv_file."
            )

        try:
            bank_account = BankAccount.objects.get(id=bank_account_id)
        except BankAccount.DoesNotExist:
            return HttpResponseBadRequest("Invalid Bank Account ID.")

        if not bank_account.csv_mapping:
            return HttpResponseBadRequest(
                f"The Bank Account '{bank_account.account_name}' does not have a default CSV Mapping configured. "
                "Please go to the Edit tab and assign one."
            )

        csv_map = bank_account.csv_mapping

        importer = TransactionImporter(csv_map, bank_account, csv_file)
        report = importer.run()

        if "error" in report:
            return JsonResponse(report, status=500)

        return JsonResponse(report, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class RecategorizeTransactionsView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            transaction_ids = body.get("transaction_ids", [])
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON body")

        if not transaction_ids:
            return JsonResponse({"message": "No transactions provided."}, status=200)

        # 1. Fetch Transactions
        transactions = Transaction.objects.filter(
            id__in=transaction_ids
        ).select_related("bank_account", "bank_account__csv_mapping")

        if not transactions.exists():
            return JsonResponse(
                {"message": "No matching transactions found."}, status=404
            )

        # 2. Initialize Service
        service = CategorizationService()

        updated_transactions = []
        stats = {
            "processed": 0,
            "updated": 0,
            "uncategorized": 0,
            "overlap": 0,
            "skipped_no_mapping": 0,
        }

        # 3. Iterate and Recalculate
        for transaction in transactions:
            stats["processed"] += 1

            # A. Resolve Mapping automatically
            bank_account = transaction.bank_account

            # If transaction has no bank account or that account has no mapping set
            if (
                not bank_account
                or not hasattr(bank_account, "csv_mapping")
                or not bank_account.csv_mapping
            ):
                stats["skipped_no_mapping"] += 1
                continue

            csv_map = bank_account.csv_mapping

            # B. Prepare Data
            t_dict = model_to_dict(transaction)

            # C. Service Logic
            cat_string = service.get_categorization_string(t_dict, csv_map)
            result = service.apply_categorization(cat_string, t_dict)

            # D. Check for Changes
            has_changed = (
                transaction.subcategory != result.subcategory
                or transaction.want_need_investment != result.want_need_investment
                or transaction.ignore != result.ignore
            )

            if has_changed:
                transaction.subcategory = result.subcategory
                transaction.want_need_investment = result.want_need_investment
                transaction.ignore = result.ignore
                updated_transactions.append(transaction)

            if result.is_uncategorized:
                stats["uncategorized"] += 1
            if result.is_category_overlap:
                stats["overlap"] += 1

        # 4. Bulk Update
        if updated_transactions:
            Transaction.objects.bulk_update(
                updated_transactions, ["subcategory", "want_need_investment", "ignore"]
            )
            stats["updated"] = len(updated_transactions)

        return JsonResponse(stats, status=200)


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
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class CreateBankAccountView(View):
    def post(self, request: WSGIRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            account_number = data.get("account_number")
            account_name = data.get("account_name")
            owners = data.get("owners", 1)
            csv_mapping_id = data.get("csv_mapping_id")

            if not account_number:
                return JsonResponse({"error": "Account Number is required"}, status=400)
            if not account_name:
                return JsonResponse({"error": "Account Name is required"}, status=400)

            csv_mapping = None
            if csv_mapping_id:
                try:
                    csv_mapping = CSVMapping.objects.get(id=csv_mapping_id)
                except CSVMapping.DoesNotExist:
                    return JsonResponse(
                        {"error": "Invalid CSV Mapping ID provided"}, status=400
                    )

            bank_account = BankAccount.objects.create(
                account_number=account_number,
                account_name=account_name,
                owners=owners,
                csv_mapping=csv_mapping,
            )

            return JsonResponse(
                {"message": "Bank Account created successfully", "id": bank_account.id},
                status=201,
            )
        except Exception as e:
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
            return JsonResponse({"error": str(e)}, status=500)
