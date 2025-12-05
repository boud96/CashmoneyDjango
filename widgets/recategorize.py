import os

import streamlit as st
import requests
from django.db.models import QuerySet

from core.base.models import Transaction, CSVMapping
from constants import URLConstants

API_URL = (
    os.getenv("API_BASE_URL", "http://localhost:8000")
    + URLConstants.RECATEGORIZE_TRANSACTIONS
)


def recategorize_tab_widget(transactions: QuerySet[Transaction]):
    transactions_uuid_list = transactions.values_list("id", flat=True)
    st.write(f"Total Transactions: {len(transactions_uuid_list)}")

    filter_fields = []
    for allowed_field in CSVMapping.ALLOWED_FIELDS:
        if st.checkbox(allowed_field, value=True):
            filter_fields.append(allowed_field)

    with st.expander("Recategorize Transactions", expanded=True):
        recategorize_unassigned = st.button("Recategorize Unassigned")

        if recategorize_unassigned:
            if not filter_fields:
                st.warning("Please select at least one field to filter by.")
                st.stop()
            if not transactions_uuid_list:
                st.warning(
                    "No transactions to recategorize."
                )  # This should never happen
                st.stop()

            try:
                payload = {"uuids": transactions_uuid_list, "fields": filter_fields}

                with st.spinner("Processing..."):
                    response = requests.post(API_URL, data=payload)

                if response.status_code == 200:
                    st.success("Recategorization completed successfully!")
                    st.json(response.json())
                else:
                    st.error(
                        f"Failed to complete recategorization! Status code: {response.status_code}"
                    )
                    st.json(response.json())  # Single st.json for error response

            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred: {e}")
