import os
import pandas as pd
import requests
import streamlit as st

from constants import URLConstants, ModelConstants
from core.base.models import Subcategory, Keyword

API_URL_CREATE = (
        os.getenv("API_BASE_URL", "http://localhost:8123/") + URLConstants.CREATE_KEYWORDS
)
API_URL_DELETE = (
        os.getenv("API_BASE_URL", "http://localhost:8123/") + URLConstants.DELETE_KEYWORDS
)

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

    with st.form(key='keyword_form'):
        st.header("Keyword Details")

        description = st.text_input(
            label="Description",
            max_chars=128
        )

        subcategory_col, wni_col = st.columns(2)
        with subcategory_col:
            selected_subcategory_label = st.selectbox(
                label="Subcategory",
                options=subcategory_display_options,
                index=0,
                key='subcategory_select'
            )

        with wni_col:
            selected_wni_label = st.selectbox(
                label="Want/Need/Investment (WNI)",
                options=wni_labels,
                index=0,
                key='wni_select'
            )

        ignore = st.checkbox(
            label="Mark as ignored",
            value=False
        )

        st.subheader("Rules for Matching")
        st.markdown("Enter a single word or phrase per cell.")

        default_rules_data = pd.DataFrame({
            ModelConstants.INCLUDE_RULE_KEY: pd.Series(dtype="str"),
            ModelConstants.EXCLUDE_RULE_KEY: pd.Series(dtype="str"),
        })

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
                )
            },
            num_rows="dynamic",
            use_container_width=True
        )

        is_keyword_submitted = st.form_submit_button("Submit")

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
        elif subcategory_id_for_payload is None or selected_subcategory_label == "--- Select Subcategory ---":
            st.error("Please select a valid Subcategory.")
        else:
            final_rules = {
                ModelConstants.INCLUDE_RULE_KEY: [
                    str(item).strip() for item in rules_df[ModelConstants.INCLUDE_RULE_KEY] if item
                ],
                ModelConstants.EXCLUDE_RULE_KEY: [
                    str(item).strip() for item in rules_df[ModelConstants.EXCLUDE_RULE_KEY] if item
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
                response = requests.post(API_URL_CREATE, json=keyword_payload, timeout=5)

                if response.status_code == 201:
                    st.success(f"Keyword '{description}' created successfully.")
                else:
                    st.error(f"Failed to create keyword. Status Code: {response.status_code}")
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")


def delete_keyword_tab_widget():
    # --- Data Fetching ---
    try:
        keywords = Keyword.objects.all().select_related('subcategory').order_by('description')

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

            data.append({
                "Select": False,
                "ID": str(k.id),
                "Description": k.description,
                "Subcategory": str(k.subcategory),
                "WNI": k.get_want_need_investment_display() or "-",
                "Include": include_str,
                "Exclude": exclude_str,
            })

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Connection Error: Could not reach Django backend. {e}")
        return

    # --- Form Structure ---
    st.title("Delete Keywords")
    st.markdown("Select the keywords you wish to remove from the database.")

    with st.form(key='delete_keyword_form'):

        # Configure the editor
        edited_df = st.data_editor(
            data=df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?",
                    help="Check to mark for deletion",
                    default=False,
                ),
                "ID": None,
                "Description": st.column_config.TextColumn(
                    "Description",
                    disabled=True
                ),
                "Subcategory": st.column_config.TextColumn(
                    "Subcategory",
                    disabled=True
                ),
                "WNI": st.column_config.TextColumn(
                    "WNI",
                    disabled=True
                ),
                "Include": st.column_config.TextColumn(
                    "Include keywords",
                    disabled=True
                ),
                "Exclude": st.column_config.TextColumn(
                    "Exclude keywords",
                    disabled=True
                ),
            },
            hide_index=True,
            use_container_width=True,
        )

        selected_rows = edited_df[edited_df["Select"] == True]
        count = len(selected_rows)

        delete_button_label = f"Delete {count} Selected Keywords" if count > 0 else "Delete Selected"
        is_delete_submitted = st.form_submit_button(delete_button_label, type="primary")

    # --- Submission Logic ---
    if is_delete_submitted:
        if count == 0:
            st.warning("Please select at least one keyword to delete.")
        else:
            # Extract IDs of selected rows
            ids_to_delete = selected_rows["ID"].tolist()

            payload = {"ids": ids_to_delete}

            try:
                response = requests.post(API_URL_DELETE, json=payload, timeout=10)

                if response.status_code == 200:
                    st.success(f"Successfully deleted {count} keywords.")
                    # Rerun to refresh the table
                    st.rerun()
                else:
                    st.error(f"Failed to delete keywords. Status Code: {response.status_code}")
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: Could not reach Django backend. {e}")
