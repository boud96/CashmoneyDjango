import streamlit as st
import requests
from core.base.models import CSVMapping, BankAccount
from core.urls import URLConstant

full_url = "http://127.0.0.1:8000/" + URLConstant.IMPORT_TRANSACTIONS  # TODO: Let backend handle this

with st.form("import_csv_form"):
    st.title("Import CSV")

    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    mappings = CSVMapping.get_csv_mappings()
    mapping_dict = {mapping.name: mapping for mapping in mappings}
    selected_name = st.selectbox("Select CSV Mapping", options=list(mapping_dict.keys()))
    selected_mapping = mapping_dict[selected_name]

    bank_accounts = BankAccount.get_bank_accounts()
    bank_account_dict = {account.account_name: account for account in bank_accounts}
    bank_account = st.selectbox("Select Bank Account", options=list(bank_account_dict))
    selected_bank_account = bank_account_dict[bank_account]

    submitted = st.form_submit_button("Submit")

    if submitted:
        if uploaded_file is None:
            st.error("Please upload a valid CSV file.")
        else:
            try:
                payload = {
                    "id": str(selected_mapping.id),
                    "bank_account_id": str(selected_bank_account.id),
                }
                files = {"csv_file": uploaded_file}

                st.spinner("Submitting data...")
                response = requests.post(full_url, data=payload, files=files)

                if response.status_code == 201:
                    st.success("Data submitted successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Failed to submit data! Status code: {response.status_code}")
                    st.json(response.json())
            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred: {e}")
