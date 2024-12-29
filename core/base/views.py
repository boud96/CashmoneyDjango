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

                transaction_data = {
                    "original_id": original_id,
                    "date_of_submission": date_of_submission,
                    "date_of_transaction": date_of_transaction,
                    "amount": amount,
                    "currency": currency,
                    "bank_account": bank_account_obj,
                    # TODO: Add other fields here
                }

                transaction = Transaction(**transaction_data)
                transactions.append(transaction)

            Transaction.objects.bulk_create(transactions)

            return JsonResponse({"success": "Transactions imported successfully"}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
