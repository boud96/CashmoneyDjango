import pandas as pd
import streamlit as st
import plotly.express as px
from django.db.models import QuerySet


class DataFrameWidget:
    DATE_COL = "date_of_transaction"
    ACCOUNT_COL = "account_name"
    CATEGORY_COL = "category_name"
    SUBCATEGORY_COL = "subcategory_name"
    COUNTERPARTY_COL = "counterparty_name"
    COUNTERPARTY_NOTE_COL = "counterparty_note"
    MY_NOTE_COL = "my_note"
    OTHER_NOTE_COL = "other_note"
    AMOUNT_COL = "effective_amount"
    WANT_NEED_INVESTMENT_COL = "want_need_investment"

    COLUMN_DISPLAY_NAMES = {
        DATE_COL: "Date",
        ACCOUNT_COL: "Account",
        CATEGORY_COL: "Category",
        SUBCATEGORY_COL: "Subcategory",
        COUNTERPARTY_COL: "Counterparty",
        COUNTERPARTY_NOTE_COL: "Counterparty Note",
        MY_NOTE_COL: "My Note",
        OTHER_NOTE_COL: "Other Note",
        AMOUNT_COL: "Amount",
        WANT_NEED_INVESTMENT_COL: "W / N / I",
    }

    def __init__(self, transactions: QuerySet):
        self.transactions = transactions
        self._df = None

    @property
    def df(self):
        """Convert the QuerySet to a DataFrame."""
        if self._df is None:
            if not self.transactions.exists():
                self._df = pd.DataFrame()
            else:
                self._df = pd.DataFrame.from_records(self.transactions.values())
        return self._df

    def _name_colors(self, column_name):
        """Assign unique colors to each unique value in a specified column."""
        unique_values = self.df[column_name].unique()
        swatches = (
            px.colors.qualitative.Prism
            + px.colors.qualitative.Vivid
            + px.colors.qualitative.Pastel
            + px.colors.qualitative.Safe
        )

        color_map = {value: color for value, color in zip(unique_values, swatches)}

        if None in color_map:
            color_map[None] = "#808080"

        return color_map

    def _style_names(self, val, column_name):
        """Apply unique background colors to each value based on the column."""
        colors = self._name_colors(column_name)
        return f"background-color: {colors.get(val, '')}"

    @staticmethod
    def _style_amount(val):
        """Highlight positive scores in green and negative in red."""
        color = "green" if val > 0 else "red"
        return f"color: {color}"

    def _rename_columns(self):
        """Rename DataFrame columns to more user-friendly display names."""
        renamed_df = self.df.rename(columns=self.COLUMN_DISPLAY_NAMES)
        self._df = renamed_df

    def _create_styled_dataframe(self):
        """Style the transactions DataFrame and render it in Streamlit."""
        styled_df = (
            self.df.style.map(
                lambda val: self._style_names(
                    val, self.COLUMN_DISPLAY_NAMES[self.ACCOUNT_COL]
                ),
                subset=[self.COLUMN_DISPLAY_NAMES[self.ACCOUNT_COL]],
            )
            .map(
                lambda val: self._style_names(
                    val, self.COLUMN_DISPLAY_NAMES[self.CATEGORY_COL]
                ),
                subset=[self.COLUMN_DISPLAY_NAMES[self.CATEGORY_COL]],
            )
            .map(
                lambda val: self._style_names(
                    val, self.COLUMN_DISPLAY_NAMES[self.SUBCATEGORY_COL]
                ),
                subset=[self.COLUMN_DISPLAY_NAMES[self.SUBCATEGORY_COL]],
            )
            .map(
                lambda val: self._style_names(
                    val, self.COLUMN_DISPLAY_NAMES[self.WANT_NEED_INVESTMENT_COL]
                ),
                subset=[self.COLUMN_DISPLAY_NAMES[self.WANT_NEED_INVESTMENT_COL]],
            )
            .map(
                self._style_amount, subset=[self.COLUMN_DISPLAY_NAMES[self.AMOUNT_COL]]
            )
        ).format(
            {
                self.COLUMN_DISPLAY_NAMES[self.AMOUNT_COL]: "{:.2f}",
                self.COLUMN_DISPLAY_NAMES[self.DATE_COL]: lambda x: x.strftime(
                    "%Y-%m-%d"
                ),
            }
        )

        return styled_df

    def _order_columns(self):
        """Reorder the columns of the DataFrame."""
        if self.df.empty:
            return

        columns = [
            self.DATE_COL,
            self.CATEGORY_COL,
            self.SUBCATEGORY_COL,
            self.ACCOUNT_COL,
            self.WANT_NEED_INVESTMENT_COL,
            self.AMOUNT_COL,
            self.COUNTERPARTY_COL,
            self.COUNTERPARTY_NOTE_COL,
            self.MY_NOTE_COL,
            self.OTHER_NOTE_COL,
        ]

        ordered_columns = [col for col in columns if col in self.df.columns]
        self._df = self.df[ordered_columns]

    def place_widget(self):
        """Call the method to create and render the styled dataframe."""
        if not self.df.empty:
            self._order_columns()
            self._rename_columns()
            styled_df = self._create_styled_dataframe()

            st.dataframe(styled_df, hide_index=True)
