import os

import streamlit as st
import requests
from constants import URLConstants

# TODO: Constant
API_URL = (
    os.getenv("API_BASE_URL", "http://localhost:8000")
    + URLConstants.RECATEGORIZE_TRANSACTIONS
)


def recategorize_tab_widget(transactions):
    st.header("Recategorize Filtered View")

    # 1. Validation and Stats
    if not transactions:
        st.info("No transactions available in the current filter to recategorize.")
        return

    try:
        count = len(transactions)

        if hasattr(transactions, "values_list"):
            transaction_ids = list(transactions.values_list("pk", flat=True))
            transaction_ids = [str(pk) for pk in transaction_ids]
        else:
            transaction_ids = [str(t.id) for t in transactions]

    except Exception as e:
        st.error(f"Could not extract transaction IDs: {e}")
        return

    if st.button(f"Recategorize {count} Transactions", type="primary"):
        payload = {"transaction_ids": transaction_ids}

        with st.spinner("Processing..."):
            try:
                response = requests.post(API_URL, json=payload, timeout=60)

                if response.status_code == 200:
                    data = response.json()
                    st.success("Analysis Complete!")

                    # Metrics
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Processed", data.get("processed", 0))
                    c2.metric("Updated", data.get("updated", 0))
                    c3.metric("Uncategorized", data.get("uncategorized", 0))
                    c4.metric("Overlaps", data.get("overlap", 0))

                    skipped = data.get("skipped_no_mapping", 0)
                    if skipped > 0:
                        st.warning(
                            f"{skipped} transactions were skipped because their Bank Account has no CSV Mapping assigned."
                        )

                    if data.get("updated", 0) > 0:
                        st.balloons()
                else:
                    st.error(f"Failed. Status: {response.status_code}")
                    with st.expander("Details"):
                        st.write(response.text)

            except requests.exceptions.RequestException as e:
                st.error(f"Connection Error: {e}")
