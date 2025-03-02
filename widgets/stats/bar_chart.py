from widgets.stats.base_widget import BaseWidget
import pandas as pd
import streamlit as st
from django.db.models import QuerySet


class BarChartWidget(BaseWidget):
    def __init__(self, transactions: QuerySet):
        super().__init__(transactions)

    def make_df(self):
        if not self.transactions.exists():
            return pd.DataFrame()

        data = pd.DataFrame.from_records(self.transactions.values("date_of_transaction", "effective_amount"))
        data["effective_amount"] = data["effective_amount"].astype(float)

        data["date_of_transaction"] = pd.to_datetime(data["date_of_transaction"])
        data["month_year"] = data["date_of_transaction"].dt.to_period("M")

        grouped = data.groupby("month_year")[
            "effective_amount"
        ].agg(
            Sum_Positive=lambda x: x[x > 0].sum(),
            Sum_Negative=lambda x: x[x < 0].sum(),
        ).reset_index()

        all_months = pd.date_range(
            start=data["month_year"].min().start_time,
            end=data["month_year"].max().end_time,
            freq="M").to_period("M")

        full_range = pd.DataFrame(all_months, columns=["month_year"])
        grouped = full_range.merge(grouped, on="month_year", how="left")

        grouped["Sum_Positive"] = grouped["Sum_Positive"].fillna(0)
        grouped["Sum_Negative"] = grouped["Sum_Negative"].fillna(0)
        grouped["Difference"] = grouped["Sum_Positive"] + grouped["Sum_Negative"]

        grouped[["Sum_Positive", "Sum_Negative", "Difference"]] = grouped[
            ["Sum_Positive", "Sum_Negative", "Difference"]
        ].astype(float)

        grouped["month_year"] = grouped["month_year"].astype(str)

        return grouped.set_index("month_year")

    def place_widget(self):
        st.bar_chart(
            self.make_df(),
            color=["#000000", "#ffabab", "#3dd56d"],
            stack="layered",
        )
