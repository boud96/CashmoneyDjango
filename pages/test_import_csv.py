import streamlit as st
import pandas as pd
import io

from django.contrib.sites import requests

from core.base.models import BankAccount

# Define choices for the 'want_need_investment' field
WNI_CHOICES = [("Want", "Want"), ("Need", "Need"), ("Investment", "Investment")]


# Streamlit form to upload CSV and map columns to model fields
def map_csv_to_model():
    st.title("Import CSV and Map to Django Model")

    # Step 1: File Upload
    encoding = st.text_input("CSV Encoding", "utf-8")
    header = st.number_input("Header", 0)
    delimiter = st.text_input("Delimiter", ",")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is not None:
        # Read the CSV file into a pandas DataFrame
        # Load the CSV file with preprocessing
        uploaded_file.seek(0)  # Ensure we read the file from the start
        raw_data = uploaded_file.read().decode(encoding)  # Decode using the correct encoding

        # Preprocess: Remove extra trailing semicolons
        cleaned_data = "\n".join(line.rstrip(";") for line in raw_data.splitlines())

        df = pd.read_csv(io.StringIO(cleaned_data), encoding=encoding, header=header, delimiter=delimiter,  on_bad_lines="warn",)

        st.write("Data preview:")
        st.dataframe(df.head(100))

        # Step 2: Create a form for mapping columns
        st.subheader("Map CSV columns to model fields")
        req_field_options = df.columns
        opt_field_options = ["None"] + list(df.columns)
        bank_account_options = BankAccount.get_bank_accounts()

        # Checkbox for dynamic input handling
        merge_acc_num_bank_code = st.checkbox(
            "One column for account number and bank code",
            key="merge_account_number_bank_code",
        )
        # Checkbox for uui

        # Dynamic form display
        with st.form("csv_mapping_form"):
            form_data = {}
            form_data["original_id"] = st.selectbox("original_id", opt_field_options)

            form_data["date_of_submission"] = st.selectbox("date_of_submission", opt_field_options)
            form_data["date_of_transaction"] = st.selectbox("date_of_transaction", req_field_options)

            form_data["bank_account"] = st.selectbox(
                "Select Bank Account",
                options=bank_account_options,
                format_func=lambda x: x[1] if x else "None"
            )

            # Conditionally show fields based on the checkbox state
            if merge_acc_num_bank_code:
                # If checked, map a single combined column
                form_data["counterparty_acc_bank_combined"] = st.selectbox(
                    "Counterparty Account Number and Bank Code (combined)",
                    opt_field_options,
                )
            else:
                # If unchecked, map separate fields
                form_data["counterparty_account_number"] = st.selectbox(
                    "counterparty_account_number", req_field_options
                )
                form_data["counterparty_bank_code"] = st.selectbox(
                    "counterparty_bank_code", req_field_options
                )
            form_data["encoding"] = encoding
            form_data["header"] = header
            form_data["delimiter"] = delimiter
            form_data["uploaded_file"] = uploaded_file
            form_data["counterparty_name"] = st.selectbox("counterparty_name", opt_field_options)
            form_data["transaction_type"] = st.selectbox("transaction_type", opt_field_options)
            form_data["variable_symbol"] = st.selectbox("variable_symbol", opt_field_options)
            form_data["specific_symbol"] = st.selectbox("specific_symbol", opt_field_options)
            form_data["constant_symbol"] = st.selectbox("constant_symbol", opt_field_options)
            form_data["counterparty_note"] = st.selectbox("counterparty_note", opt_field_options)
            form_data["my_note"] = st.selectbox("my_note", opt_field_options)
            form_data["other_note"] = st.multiselect("other_note", opt_field_options)
            form_data["amount"] = st.selectbox("amount", req_field_options)
            form_data["currency"] = st.selectbox("currency", req_field_options)

            # Submit button
            submitted = st.form_submit_button("Submit")

            if submitted:
                st.success("Mapping submitted successfully!")
                st.write("You selected the following mappings:")
                st.write(form_data)
                # Further processing can be added here (e.g., saving the data)

                django_url = "http://127.0.0.1:8000/create-entry/"
                try:
                    # Make the POST request
                    response = requests.post(django_url, json=form_data)

                    # Check response status
                    if response.status_code == 201:
                        st.success("Data submitted successfully!")
                        st.json(response.json())  # Display response data
                    else:
                        st.error("Failed to submit data!")
                        st.json(response.json())  # Display error details
                except requests.exceptions.RequestException as e:
                    st.error(f"An error occurred: {e}")

map_csv_to_model()