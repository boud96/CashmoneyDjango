import pandas as pd
import streamlit as st
import plotly.express as px
from django.db.models import QuerySet


class DataFrameWidget:
    def __init__(self, transactions: QuerySet):
        self.transactions = transactions
        self._df = None  # Internal DataFrame storage

    @property  # Changed from cached_property to regular property
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
        return {
            value: color
            for value, color in zip(unique_values, px.colors.qualitative.Prism)
        }

    def _style_names(self, val, column_name):
        """Apply unique background colors to each value based on the column."""
        colors = self._name_colors(column_name)
        return f"background-color: {colors.get(val, '')}"

    @staticmethod
    def _style_amount(val):
        """Highlight positive scores in green and negative in red."""
        color = "green" if val > 0 else "red"
        return f"color: {color}"

    def _create_styled_dataframe(self):
        """Style the transactions DataFrame and render it in Streamlit."""
        styled_df = (
            self.df.style.map(
                lambda val: self._style_names(val, "account_name"),
                subset=["account_name"],
            )
            .map(
                lambda val: self._style_names(val, "category_name"),
                subset=["category_name"],
            )
            .map(
                lambda val: self._style_names(val, "subcategory_name"),
                subset=["subcategory_name"],
            )
            .map(self._style_amount, subset=["effective_amount"])
        ).format(
            {
                "effective_amount": "{:.2f}",
                "date_of_transaction": lambda x: x.strftime("%Y-%m-%d"),
            }
        )

        st.dataframe(styled_df, hide_index=True)
        return styled_df

    def place_widget(self):
        """Call the method to create and render the styled dataframe."""
        if not self.df.empty:
            self._order_columns()
            self._create_styled_dataframe()

    def _order_columns(self):
        """Reorder the columns of the DataFrame."""
        if self.df.empty:
            return

        columns = [
            "date_of_transaction",
            "account_name",
            "category_name",
            "subcategory_name",
            "counterparty_name",
            "counterparty_note",
            "my_note",
            "other_note",
            "effective_amount",
        ]

        existing_columns = [col for col in columns if col in self.df.columns]

        # TODO: Remove adding remaining columns after all columns are styled.
        # TODO: Here the warning "Serialization of dataframe to Arrow table" comes from
        # Add remaining columns that aren't in the priority list
        remaining_columns = [col for col in self.df.columns if col not in columns]
        # Combine prioritized columns with remaining columns
        ordered_columns = existing_columns + remaining_columns

        self._df = self.df[ordered_columns]
