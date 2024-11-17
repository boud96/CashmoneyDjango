import os

import pandas as pd
import streamlit as st
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
import django

django.setup()
from core.base.models import Transaction



def get_transactions_from_db() -> pd.DataFrame:
    return pd.DataFrame.from_records(
        list(
            Transaction.objects.values(
                "date_of_transaction", "amount", "currency", "counterparty_name", "counterparty_note", "my_note", "other_note"
            )
        )
    )

def show_transactions(transactions_df: pd.DataFrame) -> None:
    st.subheader(f"Transactions")
    st.dataframe(transactions_df)
    st.write("---")




def main():
    # Title
    st.set_page_config(
        page_title="Monitor Database Annotations", layout="wide", page_icon="📀"
    )
    st.title("Custom dashboard")


    # Transactions
    transactions = get_transactions_from_db()
    show_transactions(transactions)


if __name__ == "__main__":
    main()
