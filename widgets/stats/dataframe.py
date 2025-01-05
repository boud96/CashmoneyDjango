from functools import cached_property

import pandas as pd
import streamlit as st
import plotly.express as px
from django.db.models import QuerySet


class DataFrameWidget:
    def __init__(self, transactions: QuerySet):
        self.transactions = transactions

    @cached_property
    def df(self):
        """Convert the QuerySet to a DataFrame."""
        if not self.transactions.exists():
            return pd.DataFrame()

        # Convert QuerySet to DataFrame, keeping all columns
        data = pd.DataFrame.from_records(self.transactions.values())

        return data

    def name_colors(self, column_name):
        """Assign unique colors to each unique value in a specified column."""
        unique_values = self.df[column_name].unique()
        return {value: color for value, color in zip(unique_values, px.colors.qualitative.Prism)}

    def style_names(self, val, column_name):
        """Apply unique background colors to each value based on the column."""
        colors = self.name_colors(column_name)
        return f"background-color: {colors.get(val, '')}"

    @staticmethod
    def style_amount(val):
        """Highlight positive scores in green and negative in red."""
        color = "green" if val > 0 else "red"
        return f"color: {color}"

    def create_styled_dataframe(self):
        """Style the transactions DataFrame and render it in Streamlit."""
        styled_df = (
            self.df.style
            .applymap(lambda val: self.style_names(val, "account_name"), subset=["account_name"])
            .applymap(lambda val: self.style_names(val, "category_name"), subset=["category_name"])
            .applymap(lambda val: self.style_names(val, "subcategory_name"), subset=["subcategory_name"])
            .applymap(self.style_amount, subset=["amount"])
        )  # TODO: Add more columns to style and only keep relevant ones

        # Render styled dataframe
        st.dataframe(styled_df)
        return styled_df

    def place_widget(self):
        """Call the method to create and render the styled dataframe."""
        if not self.df.empty:
            self.create_styled_dataframe()
