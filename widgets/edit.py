import os
import pandas as pd
import requests
import streamlit as st

from constants import URLConstants, ModelConstants
from core.base.models import (
    Subcategory,
    Keyword,
    Category,
    BankAccount,
    CSVMapping,
    Tag,
)

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8123/")
API_URL_CREATE_KEYWORD = BASE_URL + URLConstants.CREATE_KEYWORDS
API_URL_DELETE_KEYWORD = BASE_URL + URLConstants.DELETE_KEYWORDS
API_URL_CREATE_CATEGORY = BASE_URL + URLConstants.CREATE_CATEGORY
API_URL_DELETE_CATEGORIES = BASE_URL + URLConstants.DELETE_CATEGORIES
API_URL_CREATE_SUBCATEGORY = BASE_URL + URLConstants.CREATE_SUBCATEGORY
API_URL_DELETE_SUBCATEGORIES = BASE_URL + URLConstants.DELETE_SUBCATEGORIES
API_URL_CREATE_BANK_ACCOUNT = BASE_URL + URLConstants.CREATE_BANK_ACCOUNT
API_URL_DELETE_BANK_ACCOUNTS = BASE_URL + URLConstants.DELETE_BANK_ACCOUNTS
API_URL_CREATE_CSV_MAPPING = BASE_URL + URLConstants.CREATE_CSV_MAPPING
API_URL_DELETE_CSV_MAPPINGS = BASE_URL + URLConstants.DELETE_CSV_MAPPINGS
API_URL_CREATE_TAG = BASE_URL + URLConstants.CREATE_TAG
API_URL_DELETE_TAGS = BASE_URL + URLConstants.DELETE_TAGS


def edit_tab_widget():
    # --- Data Fetching ---
    try:
        all_subs = Subcategory.objects.all()
        sub_map = {str(sub): str(sub.id) for sub in all_subs}
        subcategory_display_options = list(sub_map.keys())
    except Exception as e:
        st.error(f"Could not access Django ORM. Check environment setup. Error: {e}")
        return

    # --- Setup Constants ---
    wni_keys = [key for key, label in ModelConstants.WNI_CHOICES]
    wni_labels = [label for key, label in ModelConstants.WNI_CHOICES]

    wni_labels.insert(0, "--- Select WNI ---")
    wni_keys.insert(0, None)

    subcategory_display_options.insert(0, "--- Select Subcategory ---")

    # --- Form Structure ---
    st.title("Create New Keyword")

    with st.form(key="keyword_form"):
        st.header("Keyword Details")

        description = st.text_input(label="Description", max_chars=128)

        subcategory_col, wni_col = st.columns(2)
        with subcategory_col:
            selected_subcategory_label = st.selectbox(
                label="Subcategory",
                options=subcategory_display_options,
                index=0,
                key="subcategory_select",
            )

        with wni_col:
            selected_wni_label = st.selectbox(
                label="Want/Need/Investment (WNI)",
                options=wni_labels,
                index=0,
                key="wni_select",
            )

        ignore = st.checkbox(label="Mark as ignored", value=False)

        st.subheader("Rules for Matching")
        st.markdown("Enter a single word or phrase per cell.")

        default_rules_data = pd.DataFrame(
            {
                ModelConstants.INCLUDE_RULE_KEY: pd.Series(dtype="str"),
                ModelConstants.EXCLUDE_RULE_KEY: pd.Series(dtype="str"),
            }
        )

        rules_df = st.data_editor(
            data=default_rules_data,
            column_config={
                ModelConstants.INCLUDE_RULE_KEY: st.column_config.TextColumn(
                    f"{ModelConstants.INCLUDE_RULE_KEY.capitalize()} Keywords",
                    help="Keywords a transaction must contain (one per row).",
                ),
                ModelConstants.EXCLUDE_RULE_KEY: st.column_config.TextColumn(
                    f"{ModelConstants.EXCLUDE_RULE_KEY.capitalize()} Keywords",
                    help="Keywords a transaction must NOT contain (one per row).",
                ),
            },
            num_rows="dynamic",
        )

        is_keyword_submitted = st.form_submit_button(
            "Submit", key="submit_create_keyword"
        )

    # --- Submission Logic ---
    if is_keyword_submitted:
        subcategory_id_for_payload = sub_map.get(selected_subcategory_label)

        try:
            wni_index = wni_labels.index(selected_wni_label)
            wni_key_for_payload = wni_keys[wni_index]
        except ValueError:
            wni_key_for_payload = None

        if not description:
            st.error("Please provide a Description.")
        elif (
            subcategory_id_for_payload is None
            or selected_subcategory_label == "--- Select Subcategory ---"
        ):
            st.error("Please select a valid Subcategory.")
        else:
            final_rules = {
                ModelConstants.INCLUDE_RULE_KEY: [
                    str(item).strip()
                    for item in rules_df[ModelConstants.INCLUDE_RULE_KEY]
                    if item
                ],
                ModelConstants.EXCLUDE_RULE_KEY: [
                    str(item).strip()
                    for item in rules_df[ModelConstants.EXCLUDE_RULE_KEY]
                    if item
                ],
            }

            keyword_payload = {
                "description": description,
                "subcategory": subcategory_id_for_payload,
                "want_need_investment": wni_key_for_payload,
                "ignore": ignore,
                "rules": final_rules,
            }

            try:
                response = requests.post(
                    API_URL_CREATE_KEYWORD, json=keyword_payload, timeout=5
                )

                if response.status_code == 201:
                    st.success(f"Keyword '{description}' created successfully.")
                else:
                    st.error(
                        f"Failed to create keyword. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def delete_keyword_tab_widget():
    # --- Data Fetching ---
    try:
        keywords = (
            Keyword.objects.all().select_related("subcategory").order_by("description")
        )

        if not keywords.exists():
            st.info("No keywords defined.")
            return

        data = []
        for k in keywords:
            # Safely get rules dictionary, defaulting to empty if None
            rules = k.rules if k.rules else {}

            # Extract lists and join them into strings
            include_str = ", ".join(rules.get("include", []))
            exclude_str = ", ".join(rules.get("exclude", []))

            data.append(
                {
                    "Select": False,
                    "ID": str(k.id),
                    "Description": k.description,
                    "Subcategory": str(k.subcategory),
                    "WNI": k.get_want_need_investment_display() or "-",
                    "Include": include_str,
                    "Exclude": exclude_str,
                }
            )

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Connection Error: Could not reach Django backend. {e}")
        return

    # --- Form Structure ---
    st.title("Delete Keywords")
    st.markdown("Select the keywords you wish to remove from the database.")

    with st.form(key="delete_keyword_form"):
        # Configure the editor
        edited_df = st.data_editor(
            data=df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?", default=False, width=100, pinned=True
                ),
                "ID": None,
                "Description": st.column_config.TextColumn(
                    "Description", disabled=True
                ),
                "Subcategory": st.column_config.TextColumn(
                    "Subcategory", disabled=True
                ),
                "WNI": st.column_config.TextColumn("WNI", disabled=True),
                "Include": st.column_config.TextColumn(
                    "Include keywords", disabled=True
                ),
                "Exclude": st.column_config.TextColumn(
                    "Exclude keywords", disabled=True
                ),
            },
            hide_index=True,
        )

        selected_rows = edited_df[edited_df["Select"]]
        count = len(selected_rows)

        delete_button_label = (
            f"Delete {count} Selected Keywords" if count > 0 else "Delete Selected"
        )
        is_delete_submitted = st.form_submit_button(
            delete_button_label, type="primary", key="submit_delete_keyword"
        )

    # --- Submission Logic ---
    if is_delete_submitted:
        if count == 0:
            st.warning("Please select at least one keyword to delete.")
        else:
            # Extract IDs of selected rows
            ids_to_delete = selected_rows["ID"].tolist()

            payload = {"ids": ids_to_delete}

            try:
                response = requests.post(
                    API_URL_DELETE_KEYWORD, json=payload, timeout=10
                )

                if response.status_code == 200:
                    st.success(f"Successfully deleted {count} keywords.")
                    st.rerun(scope="fragment")
                else:
                    st.error(
                        f"Failed to delete keywords. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def create_category_tab_widget():
    # --- Form Structure ---
    st.title("Create New Category")

    with st.form(key="create_category_form"):
        st.header("Category Details")

        name = st.text_input(label="Name", max_chars=128)

        description = st.text_area(
            label="Description", help="Optional description for the category"
        )

        is_submitted = st.form_submit_button("Submit", key="submit_create_category")

    # --- Submission Logic ---
    if is_submitted:
        if not name:
            st.error("Please provide a Category Name.")
        else:
            payload = {"name": name, "description": description}

            try:
                response = requests.post(
                    API_URL_CREATE_CATEGORY, json=payload, timeout=5
                )

                if response.status_code == 201:
                    st.success(f"Category '{name}' created successfully.")

                elif response.status_code == 409:
                    st.warning(
                        f"Category '{name}' already exists. Please choose a different name."
                    )

                else:
                    st.error(
                        f"Failed to create category. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def delete_category_tab_widget():
    # --- Data Fetching ---
    try:
        categories = Category.objects.all().order_by("name")

        if not categories.exists():
            st.info("No categories defined.")
            return

        data = []
        for c in categories:
            data.append(
                {
                    "Select": False,
                    "ID": str(c.id),
                    "Name": c.name,
                    "Description": c.description or "",
                }
            )

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Connection Error: Could not reach Django backend. {e}")
        return

    # --- Form Structure ---
    st.title("Delete Categories")
    st.markdown("Select the categories you wish to remove from the database.")

    with st.form(key="delete_category_form"):
        edited_df = st.data_editor(
            data=df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?", default=False, width=100, pinned=True
                ),
                "ID": None,
                "Name": st.column_config.TextColumn("Name", disabled=True),
                "Description": st.column_config.TextColumn(
                    "Description", disabled=True
                ),
            },
            hide_index=True,
        )

        selected_rows = edited_df[edited_df["Select"]]
        count = len(selected_rows)

        delete_button_label = (
            f"Delete {count} Selected Categories" if count > 0 else "Delete Selected"
        )
        is_delete_submitted = st.form_submit_button(
            delete_button_label, type="primary", key="submit_delete_category"
        )

    # --- Submission Logic ---
    if is_delete_submitted:
        if count == 0:
            st.warning("Please select at least one category to delete.")
        else:
            ids_to_delete = selected_rows["ID"].tolist()
            payload = {"ids": ids_to_delete}

            try:
                response = requests.post(
                    API_URL_DELETE_CATEGORIES, json=payload, timeout=10
                )

                if response.status_code == 200:
                    st.success(f"Successfully deleted {count} categories.")
                    st.rerun(scope="fragment")
                else:
                    st.error(
                        f"Failed to delete categories. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def create_subcategory_tab_widget():
    # --- Data Fetching ---
    try:
        all_cats = Category.objects.all()
        cat_map = {str(c): str(c.id) for c in all_cats}
        category_display_options = list(cat_map.keys())
    except Exception as e:
        st.error(f"Could not access Django ORM. Check environment setup. Error: {e}")
        return

    category_display_options.insert(0, "--- Select Category ---")

    # --- Form Structure ---
    st.title("Create New Subcategory")

    with st.form(key="create_subcategory_form"):
        st.header("Subcategory Details")

        name = st.text_input(label="Name", max_chars=128)

        selected_category_label = st.selectbox(
            label="Parent Category", options=category_display_options, index=0
        )

        description = st.text_area(
            label="Description", help="Optional description for the subcategory"
        )

        is_submitted = st.form_submit_button("Submit", key="submit_create_subcategory")

    # --- Submission Logic ---
    if is_submitted:
        category_id_for_payload = cat_map.get(selected_category_label)

        if not name:
            st.error("Please provide a Subcategory Name.")
        elif category_id_for_payload is None:
            st.error("Please select a valid Parent Category.")
        else:
            payload = {
                "name": name,
                "description": description,
                "category_id": category_id_for_payload,
            }

            try:
                response = requests.post(
                    API_URL_CREATE_SUBCATEGORY, json=payload, timeout=5
                )

                if response.status_code == 201:
                    st.success(f"Subcategory '{name}' created successfully.")

                elif response.status_code == 409:
                    st.warning(
                        f"Subcategory '{name}' already exists. Please choose a different name."
                    )

                elif response.status_code == 404:
                    st.error("The selected Parent Category no longer exists.")

                else:
                    st.error(
                        f"Failed to create subcategory. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def delete_subcategory_tab_widget():
    # --- Data Fetching ---
    try:
        subcategories = (
            Subcategory.objects.all()
            .select_related("category")
            .order_by("category__name", "name")
        )

        if not subcategories.exists():
            st.info("No subcategories defined.")
            return

        data = []
        for s in subcategories:
            data.append(
                {
                    "Select": False,
                    "ID": str(s.id),
                    "Name": s.name,
                    "Category": s.category.name,
                    "Description": s.description or "",
                }
            )

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Connection Error: Could not reach Django backend. {e}")
        return

    # --- Form Structure ---
    st.title("Delete Subcategories")
    st.markdown("Select the subcategories you wish to remove.")

    with st.form(key="delete_subcategory_form"):
        edited_df = st.data_editor(
            data=df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?", default=False, width=100, pinned=True
                ),
                "ID": None,
                "Name": st.column_config.TextColumn("Name", disabled=True),
                "Category": st.column_config.TextColumn("Category", disabled=True),
                "Description": st.column_config.TextColumn(
                    "Description", disabled=True
                ),
            },
            hide_index=True,
        )

        selected_rows = edited_df[edited_df["Select"]]
        count = len(selected_rows)

        delete_button_label = (
            f"Delete {count} Selected Subcategories" if count > 0 else "Delete Selected"
        )

        is_delete_submitted = st.form_submit_button(
            delete_button_label, type="primary", key="submit_delete_subcategory"
        )

    # --- Submission Logic ---
    if is_delete_submitted:
        if count == 0:
            st.warning("Please select at least one subcategory to delete.")
        else:
            ids_to_delete = selected_rows["ID"].tolist()
            payload = {"ids": ids_to_delete}

            try:
                response = requests.post(
                    API_URL_DELETE_SUBCATEGORIES, json=payload, timeout=10
                )

                if response.status_code == 200:
                    st.success(f"Successfully deleted {count} subcategories.")
                    st.rerun(scope="fragment")
                else:
                    st.error(
                        f"Failed to delete subcategories. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def create_bank_account_tab_widget():
    # --- Form Structure ---
    st.title("Create New Bank Account")

    with st.form(key="create_bank_account_form"):
        st.header("Account Details")

        account_name = st.text_input(
            label="Account Name", help="e.g., Main Checking, Savings", max_chars=128
        )

        account_number = st.text_input(label="Account Number", max_chars=128)

        owners = st.number_input(label="Number of Owners", min_value=1, value=1, step=1)

        is_submitted = st.form_submit_button("Submit", key="submit_create_bank_account")

    # --- Submission Logic ---
    if is_submitted:
        if not account_name:
            st.error("Please provide an Account Name.")
        elif not account_number:
            st.error("Please provide an Account Number.")
        else:
            payload = {
                "account_name": account_name,
                "account_number": account_number,
                "owners": int(owners),
            }

            try:
                response = requests.post(
                    API_URL_CREATE_BANK_ACCOUNT, json=payload, timeout=5
                )

                if response.status_code == 201:
                    st.success(f"Bank Account '{account_name}' created successfully.")
                else:
                    st.error(
                        f"Failed to create bank account. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def delete_bank_account_tab_widget():
    # --- Data Fetching ---
    try:
        accounts = BankAccount.objects.all().order_by("account_name")

        if not accounts.exists():
            st.info("No bank accounts defined.")
            return

        data = []
        for acc in accounts:
            data.append(
                {
                    "Select": False,
                    "ID": str(acc.id),
                    "Name": acc.account_name,
                    "Number": acc.account_number,
                    "Owners": acc.owners,
                }
            )

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Connection Error: Could not reach Django backend. {e}")
        return

    # --- Form Structure ---
    st.title("Delete Bank Accounts")
    st.markdown("Select the bank accounts you wish to remove from the database.")

    with st.form(key="delete_bank_account_form"):
        edited_df = st.data_editor(
            data=df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?",
                    default=False,
                ),
                "ID": None,
                "Name": st.column_config.TextColumn("Account Name", disabled=True),
                "Number": st.column_config.TextColumn("Account Number", disabled=True),
                "Owners": st.column_config.NumberColumn(
                    "Owners", disabled=True, format="%d"
                ),
            },
            hide_index=True,
        )

        selected_rows = edited_df[edited_df["Select"]]
        count = len(selected_rows)

        delete_button_label = (
            f"Delete {count} Selected Accounts" if count > 0 else "Delete Selected"
        )
        is_delete_submitted = st.form_submit_button(
            delete_button_label, type="primary", key="submit_delete_bank_account"
        )

    # --- Submission Logic ---
    if is_delete_submitted:
        if count == 0:
            st.warning("Please select at least one account to delete.")
        else:
            ids_to_delete = selected_rows["ID"].tolist()
            payload = {"ids": ids_to_delete}

            try:
                response = requests.post(
                    API_URL_DELETE_BANK_ACCOUNTS, json=payload, timeout=10
                )

                if response.status_code == 200:
                    st.success(f"Successfully deleted {count} bank accounts.")
                    st.rerun(scope="fragment")
                else:
                    st.error(
                        f"Failed to delete bank accounts. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def create_csv_mapping_tab_widget():
    # TODO: Add help param to the input fields
    st.title("Create New CSV Mapping")
    st.markdown("Define how to parse specific bank CSV exports.")

    with st.form(key="create_csv_mapping_form"):
        # --- Section 1: File Format ---
        st.subheader("1. File Format")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Mapping Name (Required)", help="e.g., KB Bank Export")
            encoding = st.text_input(
                "Encoding", value="utf-8", help="e.g., utf-8, cp1250"
            )
        with col2:
            delimiter = st.text_input("Delimiter", value=",", max_chars=5)
            header_row = st.number_input(
                "Header Row Index", value=0, min_value=0, step=1
            )

        # --- Section 2: Dates & Amounts ---
        st.subheader("2. Dates & Money")
        col3, col4 = st.columns(2)
        with col3:
            date_of_transaction_value = st.text_input(
                "Transaction Date Column (Required)"
            )
            date_of_transaction_format = st.text_input(
                "Transaction Date Format", value="%d.%m.%Y"
            )
            amount = st.text_input("Amount Column")
            currency = st.text_input("Currency Column")
        with col4:
            date_of_submission_value = st.text_input("Submission Date Column")
            date_of_submission_format = st.text_input("Submission Date Format")

        # --- Section 3: Identifiers & Symbols ---
        st.subheader("3. Identifiers & Symbols")
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            original_id = st.text_input("Original ID Column")
        with col6:
            variable_symbol = st.text_input("Variable Symbol")
        with col7:
            constant_symbol = st.text_input("Constant Symbol")
        with col8:
            specific_symbol = st.text_input("Specific Symbol")

        # --- Section 4: Counterparty & Notes ---
        st.subheader("4. Counterparty & Details")
        col9, col10 = st.columns(2)
        with col9:
            counterparty_name = st.text_input("Counterparty Name Column")
            counterparty_account = st.text_input("Counterparty Account No.")
            counterparty_bank = st.text_input("Counterparty Bank Code")
        with col10:
            transaction_type = st.text_input("Transaction Type Column")
            my_note = st.text_input("My Note Column")
            counterparty_note = st.text_input("Counterparty Note Column")

        # --- Section 5: Configuration ---
        st.subheader("5. Advanced Configuration")

        # Categorization Fields (Multiselect)
        allowed_fields_choices = [
            "my_note",
            "other_note",
            "counterparty_note",
            "counterparty_name",
            "counterparty_account_number",
            "transaction_type",
            "variable_symbol",
            "specific_symbol",
            "constant_symbol",
        ]

        categorization_fields = st.multiselect(
            "Categorization Fields",
            options=allowed_fields_choices,
            help="Select fields used to auto-categorize transactions.",
        )

        st.caption("Other Notes (Extra columns to store)")
        # Other Note (Data Editor for list input)
        other_note_df = pd.DataFrame({"Column Names": pd.Series(dtype="str")})
        edited_other_notes = st.data_editor(
            other_note_df,
            column_config={
                "Column Names": st.column_config.TextColumn(
                    "CSV Column Name",
                    help="Add column names to be stored in 'Other Note'",
                )
            },
            num_rows="dynamic",
            key="other_notes_editor",
        )

        is_submitted = st.form_submit_button(
            "Create Mapping", key="submit_create_csv_mapping"
        )

    # --- Submission Logic ---
    if is_submitted:
        if not name:
            st.error("Please provide a Mapping Name.")
        elif not date_of_transaction_value:
            st.error("Please provide the Transaction Date Column name.")
        else:
            other_note_list = [
                str(item).strip() for item in edited_other_notes["Column Names"] if item
            ]

            payload = {
                "name": name,
                "amount": amount,
                "header": header_row,
                "my_note": my_note,
                "currency": currency,
                "encoding": encoding,
                "delimiter": delimiter,
                "other_note": other_note_list,  # Send as list
                "original_id": original_id,
                "constant_symbol": constant_symbol,
                "specific_symbol": specific_symbol,
                "variable_symbol": variable_symbol,
                "transaction_type": transaction_type,
                "counterparty_name": counterparty_name,
                "counterparty_note": counterparty_note,
                "date_of_submission_value": date_of_submission_value,
                "date_of_submission_format": date_of_submission_format,
                "date_of_transaction_value": date_of_transaction_value,
                "date_of_transaction_format": date_of_transaction_format,
                "counterparty_account_number": counterparty_account,
                "counterparty_bank_code": counterparty_bank,
                "categorization_fields": categorization_fields,
            }

            try:
                response = requests.post(
                    API_URL_CREATE_CSV_MAPPING, json=payload, timeout=5
                )

                if response.status_code == 201:
                    st.success(f"CSV Mapping '{name}' created successfully.")
                else:
                    st.error(
                        f"Failed to create mapping. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def delete_csv_mapping_tab_widget():
    # --- Data Fetching ---
    try:
        mappings = CSVMapping.objects.all().order_by("name")

        if not mappings.exists():
            st.info("No CSV Mappings defined.")
            return

        data = []
        for m in mappings:
            cat_fields_str = (
                ", ".join(m.categorization_fields) if m.categorization_fields else "-"
            )

            data.append(
                {
                    "Select": False,
                    "ID": str(m.id),
                    "Name": m.name,
                    "Delimiter": m.delimiter,
                    "Date Col": m.date_of_transaction_value,
                    "Amount Col": m.amount or "-",
                    "Cat. Fields": cat_fields_str,
                }
            )

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Connection Error: Could not reach Django backend. {e}")
        return

    # --- Form Structure ---
    st.title("Delete CSV Mappings")
    st.markdown("Select the mappings you wish to remove from the database.")

    with st.form(key="delete_csv_mapping_form"):
        edited_df = st.data_editor(
            data=df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?", default=False, width=80, pinned=True
                ),
                "ID": None,
                "Name": st.column_config.TextColumn("Name", disabled=True),
                "Delimiter": st.column_config.TextColumn(
                    "Delimiter", disabled=True, width=100
                ),
                "Date Col": st.column_config.TextColumn("Date Column", disabled=True),
                "Amount Col": st.column_config.TextColumn(
                    "Amount Column", disabled=True
                ),
                "Cat. Fields": st.column_config.TextColumn(
                    "Categorization Fields", disabled=True
                ),
            },
            hide_index=True,
        )

        selected_rows = edited_df[edited_df["Select"]]
        count = len(selected_rows)

        delete_button_label = (
            f"Delete {count} Selected Mappings" if count > 0 else "Delete Selected"
        )
        is_delete_submitted = st.form_submit_button(
            delete_button_label, type="primary", key="submit_delete_csv_mapping"
        )

    # --- Submission Logic ---
    if is_delete_submitted:
        if count == 0:
            st.warning("Please select at least one mapping to delete.")
        else:
            ids_to_delete = selected_rows["ID"].tolist()
            payload = {"ids": ids_to_delete}

            try:
                response = requests.post(
                    API_URL_DELETE_CSV_MAPPINGS, json=payload, timeout=10
                )

                if response.status_code == 200:
                    st.success(f"Successfully deleted {count} mappings.")
                    st.rerun(scope="fragment")
                else:
                    st.error(
                        f"Failed to delete mappings. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def create_tag_tab_widget():
    # --- Form Structure ---
    st.title("Create New Tag")

    with st.form(key="create_tag_form"):
        st.header("Tag Details")

        name = st.text_input(label="Name", max_chars=128)

        description = st.text_area(
            label="Description", help="Optional description for the tag"
        )

        is_submitted = st.form_submit_button("Submit", key="submit_create_tag")

    # --- Submission Logic ---
    if is_submitted:
        if not name:
            st.error("Please provide a Tag Name.")
        else:
            payload = {"name": name, "description": description}

            try:
                response = requests.post(API_URL_CREATE_TAG, json=payload, timeout=5)

                if response.status_code == 201:
                    st.success(f"Tag '{name}' created successfully.")
                else:
                    st.error(
                        f"Failed to create tag. Status Code: {response.status_code}"
                    )
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def delete_tag_tab_widget():
    st.title("Delete Tags")
    st.markdown("Select the tags you wish to remove from the database.")

    # --- Data Fetching ---
    try:
        tags = Tag.objects.all().order_by("name")

        if not tags.exists():
            st.info("No tags defined in the database.")
            return

        data = []
        for t in tags:
            data.append(
                {
                    "Select": False,
                    "ID": str(t.id),
                    "Name": t.name,
                    "Description": t.description or "",
                }
            )

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Connection Error: Could not reach Django backend. {e}")
        return

    # --- Form Structure ---
    with st.form(key="delete_tag_form"):
        edited_df = st.data_editor(
            data=df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?", default=False, width=80, pinned=True
                ),
                "ID": None,
                "Name": st.column_config.TextColumn("Name", disabled=True),
                "Description": st.column_config.TextColumn(
                    "Description", disabled=True
                ),
            },
            hide_index=True,
        )

        selected_rows = edited_df[edited_df["Select"]]
        count = len(selected_rows)

        delete_button_label = (
            f"Delete {count} Selected Tags" if count > 0 else "Delete Selected"
        )
        is_delete_submitted = st.form_submit_button(
            delete_button_label, type="primary", key="submit_delete_tag"
        )

    # --- Submission Logic ---
    if is_delete_submitted:
        if count == 0:
            st.warning("Please select at least one tag to delete.")
        else:
            ids_to_delete = selected_rows["ID"].tolist()
            payload = {"ids": ids_to_delete}

            try:
                response = requests.post(API_URL_DELETE_TAGS, json=payload, timeout=10)

                if response.status_code == 200:
                    st.toast(f"✅ Successfully deleted {count} tags.")

                    st.rerun(scope="fragment")
                else:
                    st.error(
                        f"Failed to delete tags. Status Code: {response.status_code}"
                    )
            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: {e}")
