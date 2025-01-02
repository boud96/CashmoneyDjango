import pandas as pd
import streamlit as st

from django.db.models import QuerySet, Sum
from functools import cached_property


class BarChartWidget:
    def __init__(self, transactions: QuerySet):
        self.transactions = transactions

    @cached_property
    def df(self):
        if not self.transactions.exists():
            return pd.DataFrame()

        data = pd.DataFrame.from_records(self.transactions.values("date_of_transaction", "amount"))
        data["date_of_transaction"] = pd.to_datetime(data["date_of_transaction"])
        data["month_year"] = data["date_of_transaction"].dt.to_period("M")

        grouped = data.groupby("month_year")[
            "amount"
        ].agg(
            Sum_Positive=lambda x: x[x > 0].sum(),
            Sum_Negative=lambda x: x[x < 0].sum(),
        ).reset_index()

        grouped["Difference"] = grouped["Sum_Positive"] + grouped["Sum_Negative"]
        grouped["month_year"] = grouped["month_year"].astype(str)

        grouped[["Sum_Positive", "Sum_Negative", "Difference"]] = grouped[
            ["Sum_Positive", "Sum_Negative", "Difference"]
        ].astype(float)

        return grouped.set_index("month_year")

    def place_widget(self):
        if self.df.empty:
            st.write("No data available to display.")
        else:
            st.bar_chart(
                self.df,
                color=["#000000", "#ffabab", "#3dd56d"],
                stack="layered",
            )
