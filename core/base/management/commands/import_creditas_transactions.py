import pandas as pd
from django.core.management.base import BaseCommand
from core.base.models import Transaction
from datetime import datetime


class Command(BaseCommand):
    help = "Import transactions from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        # Load CSV data with pandas
        df = pd.read_csv(csv_file)

        # Map CSV columns to model fields
        for _, row in df.iterrows():
            try:
                transaction = Transaction(
                    date_of_transaction=datetime.strptime(row['Datum zaúčtování'], '%d.%m.%Y'),
                    date_of_submission=datetime.strptime(row['Datum provedení'], '%d.%m.%Y') if pd.notna(
                        row['Datum provedení']) else None,
                    counterparty_account_number=row['Protiúčet'],
                    counterparty_bank_code=row['Protiúčet-banka'],
                    counterparty_name=row['Název protiúčtu'],
                    transaction_type=row['Kód transakce'],
                    variable_symbol=row['VS'],
                    specific_symbol=row['SS'],
                    constant_symbol=row['KS'],
                    counterparty_note=row['Zpráva pro protistranu'],
                    my_note=row['Poznámka'],
                    other_note=row.get('Kategorie', None),
                    amount=row['Částka'],
                    currency=row['Měna']
                )
                transaction.save()  # Save each transaction instance to the database
                self.stdout.write(self.style.SUCCESS(f'Successfully imported transaction {transaction.id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error importing row: {row.to_dict()}'))
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
