import streamlit as st
from widgets.filters.base import BaseFilter


class BankAccountFilter(BaseFilter):
    def __init__(self, model, label: str):
        super().__init__()
        self.model = model
        self.label = label
        self.bank_accounts = self._fetch_bank_accounts()

    def _fetch_bank_accounts(self):
        bank_accounts = {"None": "None"}
        bank_accounts.update(
            {
                str(account.id): account.account_name
                for account in self.model.objects.all().order_by("account_name")
            }
        )
        return bank_accounts

    def _update_selected(self):
        """Callback function to update session state when the pills selection changes."""
        selected = st.session_state.get("bank_account_filter")
        st.session_state["selected_bank_accounts"] = selected

    def _select_all(self):
        """Callback function to select all bank accounts."""
        options = list(self.bank_accounts.values())
        st.session_state["selected_bank_accounts"] = options

    def _deselect_all(self):
        """Callback function to deselect all bank accounts."""
        st.session_state["selected_bank_accounts"] = []

    def place_widget(self, sidebar=False):
        location = st.sidebar if sidebar else st
        options = list(self.bank_accounts.values())

        # Initialize session state for selection tracking if not already done
        if "selected_bank_accounts" not in st.session_state:
            st.session_state["selected_bank_accounts"] = options

        with location.expander(f"{self.label}", expanded=True):
            selected = st.pills(
                f"Select {self.label}",
                options,
                selection_mode="multi",
                default=st.session_state["selected_bank_accounts"],
                key="bank_account_filter",
                on_change=self._update_selected,  # Register the callback
            )

            # Columns for select/deselect buttons inside the expander
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Select All",
                    key="select_all_bank_accounts",
                    on_click=self._select_all,
                ):
                    pass  # The actual change will happen in the callback
            with col2:
                if st.button(
                    "Deselect All",
                    key="deselect_all_bank_accounts",
                    on_click=self._deselect_all,
                ):
                    pass  # The actual change will happen in the callback

            # Map selected options back to bank account IDs
            selected_ids = [
                key for key, value in self.bank_accounts.items() if value in selected
            ]
            self.set_param("bank_account", selected_ids)
