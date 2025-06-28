from datetime import timedelta

import pandas as pd

from widgets.stats.base_widget import BaseWidget
import streamlit as st
from django.db.models import QuerySet, Sum

SUM_INCOMES = "sum_of_incomes"
SUM_EXPENSES = "sum_of_expenses"
NET_SUM = "net_sum"
MONTHLY_AVG_INCOMES = "monthly_avg_incomes"
MONTHLY_AVG_EXPENSES = "monthly_avg_expenses"
MONTHLY_AVG_NET = "monthly_avg_net"


class OverviewStatsWidget(BaseWidget):
    def __init__(self, transactions: QuerySet, filter_params: dict):
        self.filter_params = filter_params
        super().__init__(transactions)

        self.stats = {}
        if len(transactions) > 0:
            self._calculate_stats()

    def _calculate_stats(self):
        sum_of_expenses = (
            self.transactions.filter(amount__lt=0).aggregate(Sum("effective_amount"))[
                "effective_amount__sum"
            ]
            or 0
        )
        sum_of_incomes = (
            self.transactions.filter(amount__gt=0).aggregate(Sum("effective_amount"))[
                "effective_amount__sum"
            ]
            or 0
        )
        net_sum = sum_of_incomes + sum_of_expenses

        sum_of_expenses_str = f"{sum_of_expenses:,.0f}".replace(",", " ")
        sum_of_incomes_str = f"{sum_of_incomes:,.0f}".replace(",", " ")
        net_sum_str = f"{net_sum:,.0f}".replace(",", " ")

        transactions_df = pd.DataFrame.from_records(self.transactions.values())
        transactions_df["date_of_transaction"] = pd.to_datetime(
            transactions_df["date_of_transaction"]
        )
        transactions_df = self._add_month_start_transactions(transactions_df)

        monthly_expenses_df = (
            transactions_df[transactions_df["amount"] <= 0]
            .groupby(transactions_df["date_of_transaction"].dt.to_period("M"))[
                "effective_amount"
            ]
            .sum()
            .reset_index(name="monthly_sum")
        )
        monthly_avg_expenses = monthly_expenses_df["monthly_sum"].mean() or 0

        monthly_incomes_df = (
            transactions_df[transactions_df["amount"] >= 0]
            .groupby(transactions_df["date_of_transaction"].dt.to_period("M"))[
                "effective_amount"
            ]
            .sum()
            .reset_index(name="monthly_sum")
        )
        monthly_avg_incomes = monthly_incomes_df["monthly_sum"].mean() or 0

        monthly_avg_net = monthly_avg_incomes + monthly_avg_expenses

        monthly_avg_expenses_str = f"{monthly_avg_expenses:,.0f}".replace(",", " ")
        monthly_avg_incomes_str = f"{monthly_avg_incomes:,.0f}".replace(",", " ")
        monthly_avg_net_str = f"{monthly_avg_net:,.0f}".replace(",", " ")

        self.stats = {
            SUM_EXPENSES: sum_of_expenses_str,
            SUM_INCOMES: sum_of_incomes_str,
            NET_SUM: net_sum_str,
            MONTHLY_AVG_EXPENSES: monthly_avg_expenses_str,
            MONTHLY_AVG_INCOMES: monthly_avg_incomes_str,
            MONTHLY_AVG_NET: monthly_avg_net_str,
        }

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

    def place_widget(self):
        if self.transactions:
            st.markdown("## Available")
            st.markdown("## :orange[TODO]")  # TODO: Add expenses

            col_1, col_2, col_3 = st.columns(3)
            with col_1:
                st.markdown("## Expenses")
                st.markdown(f"## :red[{self.stats.get(SUM_EXPENSES)}]")
                st.metric(
                    label="Monthly averages:",
                    value="",
                    delta=self.stats.get(MONTHLY_AVG_EXPENSES),
                )
            with col_2:
                st.markdown("## Sum of incomes")
                st.markdown(f"## :green[{self.stats.get(SUM_INCOMES)}]")
                st.metric(
                    label="Sum of incomes",
                    value="",
                    delta=self.stats.get(MONTHLY_AVG_INCOMES),
                    label_visibility="hidden",
                )
            with col_3:
                st.markdown("## Net")
                st.markdown(f"## :blue[{self.stats.get(NET_SUM)}]")
                st.metric(
                    label="Net value",
                    value="",
                    delta=self.stats.get(MONTHLY_AVG_NET),
                    label_visibility="hidden",
                )
