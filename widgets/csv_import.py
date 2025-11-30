import os

import streamlit as st
import requests
from core.base.models import CSVMapping, BankAccount, Transaction
from constants import URLConstants
from widgets.stats.dataframe import DataFrameWidget


API_URL = (
    os.getenv("API_BASE_URL", "http://localhost:8000")
    + URLConstants.IMPORT_TRANSACTIONS
)


def render_success_response(json_response: dict):
    st.success("Data submitted successfully!")

    st.json(json_response)  # TODO: Remove, showing for Debug
    created_message = json_response.get("created").get("message")
    created_id_list = json_response.get("created").get("transactions")

    category_overlap_message = (
        json_response.get("created").get("category_overlap").get("message")
    )

    uncategorized_message = (
        json_response.get("created").get("uncategorized").get("message")
    )

    if created_id_list:
        created_queryset = Transaction.get_transactions_from_db(
            filter_params={"id__in": created_id_list, "show_ignored": True}
        )
        st.write("CREATED TRANSACTIONS")
        DataFrameWidget(created_queryset).place_widget()

        st.write(created_message)
        st.write("of which")
        st.write(category_overlap_message)
        st.write("and")
        st.write(uncategorized_message)

    st.write("SKIPPED TRANSACTIONS")
    skipped_message = json_response.get("skipped").get("message")
    st.write(skipped_message)
    st.write("of which")
    already_imported_message = (
        json_response.get("skipped").get("already_imported").get("message")
    )
    st.write(already_imported_message)
    st.write("and")
    possible_duplicates_message = (
        json_response.get("skipped").get("possible_duplicates").get("message")
    )
    st.write(possible_duplicates_message)
    st.write("and")
    errors_message = json_response.get("skipped").get("errors").get("message")
    st.write(errors_message)


def import_form_widget():
    with st.form("import_csv_form"):
        st.title("Import CSV")

        uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

        mappings = CSVMapping.get_csv_mappings()
        mapping_dict = {mapping.name: mapping for mapping in mappings}
        selected_name = st.selectbox(
            "Select CSV Mapping", options=list(mapping_dict.keys())
        )
        selected_mapping = mapping_dict[selected_name]

        bank_accounts = BankAccount.get_bank_accounts()
        bank_account_dict = {account.account_name: account for account in bank_accounts}
        bank_account = st.selectbox(
            "Select Bank Account", options=list(bank_account_dict)
        )
        selected_bank_account = bank_account_dict[bank_account]

        submitted = st.form_submit_button("Submit")

        if submitted:
            if uploaded_file is None:
                st.error("Please upload a valid CSV file.")
            else:
                try:
                    payload = {
                        "csv_map_id": str(selected_mapping.id),
                        "bank_account_id": str(selected_bank_account.id),
                    }
                    files = {"csv_file": uploaded_file}

                    st.spinner("Submitting data...")
                    response = requests.post(API_URL, data=payload, files=files)

                    if response.status_code == 201:
                        render_success_response(response.json())
                    else:
                        st.error(
                            f"Failed to submit data! Status code: {response.status_code}"
                        )
                        st.json(response.json())
                except requests.exceptions.RequestException as e:
                    st.error(f"An error occurred: {e}")
