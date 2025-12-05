import streamlit as st
from widgets.filters.base import BaseFilter


class BankAccountFilter(BaseFilter):
    def __init__(self, model, label: str):
        super().__init__()
        self.model = model
        self.label = label
        self.bank_accounts = self._fetch_bank_accounts()
        self.widget_key = "bank_account_filter"

    def _fetch_bank_accounts(self):
        bank_accounts = {"None": "None"}
        bank_accounts.update(
            {
                str(account.id): account.account_name
                for account in self.model.objects.all().order_by("account_name")
            }
        )
        return bank_accounts

    def place_widget(self, sidebar=False):
        location = st.sidebar if sidebar else st
        options = list(self.bank_accounts.values())

        if self.widget_key not in st.session_state:
            st.session_state[self.widget_key] = options

        with location.expander(f"{self.label}", expanded=True):
            selected = st.pills(
                f"Select {self.label}",
                options,
                selection_mode="multi",
                key=self.widget_key,
            )

            col1, col2 = st.columns(2)
            with col1:
                st.button(
                    "Select All",
                    key="select_all_bank_accounts",
                    on_click=self.select_all,
                    args=(self.widget_key, options),
                )
            with col2:
                st.button(
                    "Deselect All",
                    key="deselect_all_bank_accounts",
                    on_click=self.deselect_all,
                    args=(self.widget_key,),
                )

            selected_ids = [
                key for key, value in self.bank_accounts.items() if value in selected
            ]
            self.set_param("bank_account", selected_ids)
