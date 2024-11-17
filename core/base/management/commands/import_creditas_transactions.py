import warnings
import pandas as pd
from django.core.management.base import BaseCommand

from core.base.models import Transaction, BankAccount
from datetime import datetime

from core.utils import get_matching_keyword_objs


class CSVColumns:
    ACCOUNT_NUMBER = "Můj účet"
    BANK_CODE = "Můj účet-banka"
    DATE_OF_TRANSACTION = "Datum zaúčtování"
    DATE_OF_SUBMISSION = "Datum provedení"
    COUNTERPARTY_ACCOUNT_NUMBER = "Protiúčet"
    COUNTERPARTY_BANK_CODE = "Protiúčet-banka"
    COUNTERPARTY_NAME = "Název protiúčtu"
    TRANSACTION_TYPE = "Kód transakce"
    VARIABLE_SYMBOL = "VS"
    SPECIFIC_SYMBOL = "SS"
    CONSTANT_SYMBOL = "KS"
    COUNTERPARTY_NOTE = "Zpráva pro protistranu"
    MY_NOTE = "Poznámka"
    AMOUNT = "Částka"
    CURRENCY = "Měna"


class Command(BaseCommand):
    # TODO: Make this available in the admin interface
    # TODO: Make it universal for other banks - form to define columns
    help = "Import transactions from a CSV file --csv_file <path_to_csv_file> --encoding <encoding> (default: utf-8)"

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Path to the CSV file')
        parser.add_argument('--encoding', type=str, default='utf-8', help='Encoding of the CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv']
        encoding = kwargs['encoding']

        df = pd.read_csv(csv_file, encoding=encoding, keep_default_na=False)
        df = df.replace("", None)
        df = df.where(pd.notna(df), None)

        # Map CSV columns to model fields
        success_count = 0
        unsuccess_count = 0
        skipped_count = 0
        for _, row in df.iterrows():
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)

                    # Check if the transaction already exists
                    existing_transaction = Transaction.objects.filter(
                        date_of_transaction=datetime.strptime(row[CSVColumns.DATE_OF_TRANSACTION], '%d.%m.%Y'),
                        counterparty_account_number=row[CSVColumns.COUNTERPARTY_ACCOUNT_NUMBER],
                        amount=row[CSVColumns.AMOUNT],
                        currency=row[CSVColumns.CURRENCY],
                        variable_symbol=row[CSVColumns.VARIABLE_SYMBOL],
                        specific_symbol=row[CSVColumns.SPECIFIC_SYMBOL],
                        constant_symbol=row[CSVColumns.CONSTANT_SYMBOL],
                    ).first()
                    if existing_transaction:
                        skipped_count += 1
                        self.stdout.write(self.style.WARNING(f'Transaction already exists: {row.to_dict()}'))

                    if not existing_transaction:
                        bank_account = BankAccount.objects.filter(
                            account_number=row[CSVColumns.ACCOUNT_NUMBER],
                            bank_code=row[CSVColumns.BANK_CODE]
                        ).first()

                        # Categorize subcategory TODO: Categorize WNI and tags
                        subcategory = None
                        want_need_investment = None
                        matching_keywords = get_matching_keyword_objs([row[CSVColumns.COUNTERPARTY_NOTE]])
                        if len(matching_keywords) > 1:
                            self.stdout.write(self.style.WARNING(f'Multiple keywords found: {matching_keywords}'))
                            pass
                        elif len(matching_keywords) == 0:
                            self.stdout.write(self.style.WARNING(f'No keywords found'))
                            pass
                        else:
                            subcategory = matching_keywords[0].subcategory
                            want_need_investment = matching_keywords[0].want_need_investment

                        transaction = Transaction(
                            date_of_transaction=datetime.strptime(row[CSVColumns.DATE_OF_TRANSACTION], '%d.%m.%Y'),
                            date_of_submission=datetime.strptime(row[CSVColumns.DATE_OF_SUBMISSION],
                                                                 '%d.%m.%Y') if pd.notna(
                                row[CSVColumns.DATE_OF_SUBMISSION]) else None,

                            bank_account=bank_account,

                            counterparty_account_number=row[CSVColumns.COUNTERPARTY_ACCOUNT_NUMBER],
                            counterparty_bank_code=row[CSVColumns.COUNTERPARTY_BANK_CODE],
                            counterparty_name=row[CSVColumns.COUNTERPARTY_NAME],
                            transaction_type=row[CSVColumns.TRANSACTION_TYPE],
                            variable_symbol=row[CSVColumns.VARIABLE_SYMBOL],
                            specific_symbol=row[CSVColumns.SPECIFIC_SYMBOL],
                            constant_symbol=row[CSVColumns.CONSTANT_SYMBOL],
                            counterparty_note=row[CSVColumns.COUNTERPARTY_NOTE],
                            my_note=row[CSVColumns.MY_NOTE],
                            amount=row[CSVColumns.AMOUNT],
                            currency=row[CSVColumns.CURRENCY],
                            subcategory=subcategory,
                            want_need_investment=want_need_investment,
                        )
                        transaction.save()
                        success_count += 1
            except Exception as e:
                unsuccess_count += 1
                self.stdout.write(self.style.ERROR(f'Error importing row: {row.to_dict()}'))
                self.stdout.write(self.style.ERROR(f'Error: {e}'))

        print('Import finished')
        print(f"Records in CSV: {len(df)}")
        print(f'Successfully imported {success_count} transactions')
        print(f'Failed to import {unsuccess_count} transactions')
        print(f'Skipped {skipped_count} transactions')
        if skipped_count + success_count + unsuccess_count != len(df):
            print('Discrepancy in the number of records')