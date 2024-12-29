import io
from datetime import datetime

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import CSVMapping, Transaction, BankAccount


@csrf_exempt  # TODO: Make this view secure and stuff
def import_transactions(request):
    if request.method == "POST":
        try:
            csv_mapping = CSVMapping.objects.get(id=request.POST.get("id"))
            csv_file = request.FILES.get("csv_file")

            csv_map = csv_mapping.mapping_json

            encoding = csv_mapping.mapping_json.get("encoding")
            header = csv_mapping.mapping_json.get("header")
            delimiter = csv_mapping.mapping_json.get("delimiter")

            # Trailing delimiters handle - without it, it sometimes throws an error
            raw_data = csv_file.read().decode(encoding)
            cleaned_data = "\n".join(line.rstrip(delimiter) for line in raw_data.splitlines())

            print(raw_data)

            df = pd.read_csv(
                io.StringIO(cleaned_data),
                encoding=encoding,
                header=header,
                delimiter=delimiter,
                on_bad_lines="warn"
            ).fillna('').astype(str)

            # Import data into the Transaction model
            transactions = []
            for _, row in df.iterrows():
                # TODO: Method / function for each column
                #  but might rework the CSVMap model to have fields instead of one JSON

                # TODO: If row fails, notify on frontend
                original_id = row.get(csv_map.get("original_id"))

                date_of_submission = row.get(csv_map.get("date_of_submission"))
                # convert to datetime object
                date_of_submission = datetime.strptime(date_of_submission, '%d.%m.%Y') if date_of_submission else None

                date_of_transaction = row.get(csv_map.get("date_of_transaction"))
                # convert to datetime object
                date_of_transaction = datetime.strptime(date_of_transaction, '%d.%m.%Y') if date_of_transaction else None

                amount = row.get(csv_map.get("amount"))
                if isinstance(amount, str):
                    amount = amount.replace(',', '.')
                try:
                    amount = float(amount)
                except ValueError:
                    amount = None

                currency = row.get(csv_map.get("currency"))

                bank_account = csv_map.get("bank_account")
                bank_account_obj = BankAccount.objects.get(id=bank_account)

                my_note = row.get(csv_map.get("my_note"))

                other_note_columns = csv_map.get("other_note", [])  # Expecting a list of column names
                other_note = " ".join(str(row.get(col, "")) for col in other_note_columns).strip()

                counterparty_note = row.get(csv_map.get("counterparty_note"))

                constant_symbol = row.get(csv_map.get("constant_symbol"))

                specific_symbol = row.get(csv_map.get("specific_symbol"))

                variable_symbol = row.get(csv_map.get("variable_symbol"))

                transaction_type = row.get(csv_map.get("transaction_type"))

                # TODO: Make it possible for account number and bank code to in one column
                counterparty_account_number = row.get(csv_map.get("counterparty_account_number"))

                counterparty_bank_code = row.get(csv_map.get("counterparty_bank_code"))

                counterparty_name = row.get(csv_map.get("counterparty_name"))

                transaction_data = {
                    "original_id": original_id,
                    "date_of_submission": date_of_submission,
                    "date_of_transaction": date_of_transaction,
                    "amount": amount,
                    "currency": currency,
                    "bank_account": bank_account_obj,
                    "my_note": my_note,
                    "other_note": other_note,
                    "counterparty_note": counterparty_note,
                    "constant_symbol": constant_symbol,
                    "specific_symbol": specific_symbol,
                    "variable_symbol": variable_symbol,
                    "transaction_type": transaction_type,
                    "counterparty_account_number": counterparty_account_number,
                    "counterparty_bank_code": counterparty_bank_code,
                    "counterparty_name": counterparty_name,
                }

                transaction = Transaction(**transaction_data)
                transactions.append(transaction)

            Transaction.objects.bulk_create(transactions)

            return JsonResponse({"success": "Transactions imported successfully"}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
