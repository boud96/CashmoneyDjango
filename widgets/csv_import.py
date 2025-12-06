import os
import streamlit as st
import requests
import pandas as pd
from core.base.models import CSVMapping, BankAccount, Transaction
from constants import URLConstants

API_URL = (
    os.getenv("API_BASE_URL", "http://localhost:8000")
    + URLConstants.IMPORT_TRANSACTIONS
)


def _fetch_created_transactions(id_list: list):
    """
    Helper to fetch the actual objects for the result table.
    We use the existing filter method from your model.
    """
    if not id_list:
        return None
    return Transaction.get_transactions_from_db(
        filter_params={"id__in": id_list, "show_ignored": True}
    )


def _render_import_results(data: dict):
    """
    Renders the JSON response in a visual dashboard format.
    Expects the structure returned by the TransactionImporter service.
    """
    st.divider()
    st.subheader("Import Summary")

    # 1. High-level Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Rows Processed", data.get("loaded", 0))
    col2.metric("Successfully Created", data.get("created", {}).get("count", 0))
    col3.metric("Skipped/Errors", data.get("skipped", {}).get("total", 0))

    # 2. Detailed Breakdown via Tabs
    tab_success, tab_skipped = st.tabs(["✅ Success Details", "⚠️ Skipped & Errors"])

    with tab_success:
        created_data = data.get("created", {})

        # Sub-metrics for categorization quality
        sc1, sc2 = st.columns(2)
        sc1.info(
            f"Category Overlaps: {created_data.get('category_overlap', {}).get('count', 0)}"
        )
        sc2.info(
            f"Uncategorized: {created_data.get('uncategorized', {}).get('count', 0)}"
        )

        uncategorized_list = created_data.get("uncategorized", {}).get(
            "transactions", []
        )
        if uncategorized_list:
            with st.expander("View Uncategorized Transactions"):
                st.dataframe(pd.DataFrame(uncategorized_list))

        overlap_list = created_data.get("category_overlap", {}).get("transactions", [])
        if overlap_list:
            with st.expander("View Category Overlaps"):
                st.dataframe(pd.DataFrame(overlap_list))

    with tab_skipped:
        skipped_data = data.get("skipped", {})

        # Already Imported
        already_imported_count = skipped_data.get("already_imported", 0)
        if already_imported_count > 0:
            st.warning(
                f"{already_imported_count} transactions were already in the database (Exact ID match)."
            )

        # Possible Duplicates
        duplicates_data = skipped_data.get("possible_duplicates", {})
        if duplicates_data.get("count", 0) > 0:
            with st.expander(f"Possible Duplicates ({duplicates_data.get('count')})"):
                st.caption(
                    "These matched by date, amount, and counterparty but had no original ID."
                )
                st.dataframe(pd.DataFrame(duplicates_data.get("transactions", [])))

        # Errors
        errors_data = skipped_data.get("errors", {})
        if errors_data.get("count", 0) > 0:
            with st.expander(
                f"Processing Errors ({errors_data.get('count')})", expanded=True
            ):
                st.error("The following rows failed to import:")
                st.dataframe(pd.DataFrame(errors_data.get("details", [])))


def import_form_widget():
    # --- Data Fetching ---
    try:
        mappings = CSVMapping.get_csv_mappings()
        bank_accounts = BankAccount.get_bank_accounts()
    except Exception as e:
        st.error(f"Error fetching form options: {e}")
        return

    mapping_dict = {m.name: m for m in mappings}
    account_dict = {a.account_name: a for a in bank_accounts}

    if not mapping_dict or not account_dict:
        st.warning(
            "Please ensure you have created at least one CSV Mapping and one Bank Account."
        )
        return

    # --- Form Structure ---
    st.title("Import Transactions")

    with st.form("import_csv_form"):
        st.markdown("Upload a CSV file and map it to a specific bank account.")

        col_file, col_opts = st.columns([2, 1])

        with col_file:
            uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

        with col_opts:
            selected_mapping_name = st.selectbox(
                "CSV Mapping Rule", options=list(mapping_dict.keys())
            )
            selected_account_name = st.selectbox(
                "Target Bank Account", options=list(account_dict.keys())
            )

        submitted = st.form_submit_button("Start Import", type="primary")

    # --- Submission Logic ---
    if submitted:
        if uploaded_file is None:
            st.error("Please upload a valid CSV file.")
            return

        selected_mapping = mapping_dict[selected_mapping_name]
        selected_account = account_dict[selected_account_name]

        payload = {
            "csv_map_id": str(selected_mapping.id),
            "bank_account_id": str(selected_account.id),
        }
        files = {"csv_file": uploaded_file}

        try:
            with st.spinner("Processing CSV..."):
                response = requests.post(API_URL, data=payload, files=files, timeout=30)

            if response.status_code == 201:
                st.toast("Import finished!", icon="✅")
                _render_import_results(response.json())

            elif response.status_code == 400:
                st.error("Validation Error: Please check your inputs.")
                st.write(response.text)

            else:
                st.error(f"Import Failed. Status: {response.status_code}")
            with st.expander("See Error Details"):
                try:
                    st.json(response.json())
                except ValueError:
                    st.write(response.text)

        except requests.exceptions.RequestException as e:
            st.error(f"Connection Error: Could not reach backend. {e}")
