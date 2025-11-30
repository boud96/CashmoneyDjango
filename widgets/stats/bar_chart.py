from datetime import timedelta
import altair as alt
from widgets.stats.base_widget import BaseWidget
import pandas as pd
import streamlit as st
from django.db.models import QuerySet


class BarChartWidget(BaseWidget):
    def __init__(self, transactions: QuerySet, filter_params: dict):
        self.filter_params = filter_params
        super().__init__(transactions)

    def _get_first_date(self):
        first_date = self.transactions.order_by("date_of_transaction").first()[
            "date_of_transaction"
        ]
        return first_date

    def _get_last_date(self):
        last_date = self.transactions.order_by("-date_of_transaction").first()[
            "date_of_transaction"
        ]
        return last_date

    def _add_month_start_transactions(self, transactions_df):
        first_date = self.filter_params.get("date_from")
        last_date = self.filter_params.get("date_to")

        current_date = first_date.replace(day=1)
        dates = []

        while current_date <= last_date:
            timestamp_date = pd.Timestamp(current_date)
            dates.append(timestamp_date)

            current_date += timedelta(days=32)
            current_date = current_date.replace(day=1)

        extra_transactions_df = pd.DataFrame(
            {
                "date_of_transaction": dates,
                "amount": [0] * len(dates),
                "effective_amount": [0] * len(dates),
            }
        )

        return pd.concat([transactions_df, extra_transactions_df], ignore_index=True)

    def make_df(self):
        if not self.transactions.exists():
            return pd.DataFrame()

        data = pd.DataFrame.from_records(
            self.transactions.values("date_of_transaction", "effective_amount")
        )
        data = self._add_month_start_transactions(data)
        data["effective_amount"] = data["effective_amount"].astype(float)

        data["date_of_transaction"] = pd.to_datetime(data["date_of_transaction"])
        data["month_year"] = data["date_of_transaction"].dt.to_period("M")

        grouped = (
            data.groupby("month_year")["effective_amount"]
            .agg(
                Sum_Positive=lambda x: x[x >= 0].sum(),
                Sum_Negative=lambda x: x[x <= 0].sum(),
            )
            .reset_index()
        )

        all_months = pd.date_range(
            start=data["month_year"].min().start_time,
            end=data["month_year"].max().end_time,
            freq="ME",
        ).to_period("M")

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
        df = self.make_df().reset_index()

        tooltip_config = [
            alt.Tooltip("month_year", title="Month"),
            alt.Tooltip("Sum_Positive:Q", title="Income", format=",.2f"),
            alt.Tooltip("Sum_Negative:Q", title="Expenses", format=",.2f"),
            alt.Tooltip("Difference:Q", title="Net Profit", format=",.2f"),
        ]

        base = alt.Chart(df).encode(x=alt.X("month_year", title="Month"))

        pos_neg_bars = (
            base.transform_fold(["Sum_Positive", "Sum_Negative"])
            .mark_bar(width={"band": 1})
            .encode(
                y=alt.Y(
                    "value:Q", title="Value", axis=alt.Axis(grid=True, domain=True)
                ),
                color=alt.Color(
                    "key:N",
                    scale=alt.Scale(
                        domain=["Sum_Positive", "Sum_Negative"],
                        range=["#3dd56d", "#ffabab"],
                    ),
                    legend=None,
                ),
                tooltip=tooltip_config,
            )
        )

        diff_bar = base.mark_bar(width={"band": 0.25}, color="#599af0").encode(
            y=alt.Y("Difference:Q", title="Value"), tooltip=tooltip_config
        )

        st.altair_chart(
            (pos_neg_bars + diff_bar).interactive(),
        )
