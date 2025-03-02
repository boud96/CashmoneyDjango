from functools import cached_property
import pandas as pd
from django.db.models import QuerySet

class BaseWidget:
    def __init__(self, transactions: QuerySet):
        self.transactions = transactions

    @cached_property
    def df(self):
        """Convert the QuerySet to a DataFrame."""
        if not self.transactions.exists():
            return pd.DataFrame()

        # Convert QuerySet to DataFrame, keeping all columns
        data = pd.DataFrame.from_records(self.transactions.values())

        return data