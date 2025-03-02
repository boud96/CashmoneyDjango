from widgets.stats.base_widget import BaseWidget
import streamlit as st
from django.db.models import QuerySet, Sum, Avg
from django.db.models.functions import TruncMonth

SUM_INCOMES = "sum_of_incomes"
SUM_EXPENSES = "sum_of_expenses"
NET_SUM = "net_sum"
MONTHLY_AVG_INCOMES = "monthly_avg_incomes"
MONTHLY_AVG_EXPENSES = "monthly_avg_expenses"
MONTHLY_AVG_NET = "monthly_avg_net"


#TODO: Fix - Does not include months where no transactions were made
class OverviewStatsWidget(BaseWidget):
    def __init__(self, transactions: QuerySet):
        super().__init__(transactions)

        self.stats = {}
        if len(transactions) > 0:
            self._calculate_stats()

    def _calculate_stats(self):
        sum_of_expenses = self.transactions.filter(amount__lt=0).aggregate(Sum("effective_amount"))["effective_amount__sum"] or 0
        sum_of_incomes = self.transactions.filter(amount__gt=0).aggregate(Sum("effective_amount"))["effective_amount__sum"] or 0
        net_sum = sum_of_incomes + sum_of_expenses

        sum_of_expenses_str = f"{sum_of_expenses:,.0f}".replace(",", " ")
        sum_of_incomes_str = f"{sum_of_incomes:,.0f}".replace(",", " ")
        net_sum_str = f"{net_sum:,.0f}".replace(",", " ")

        monthly_avg_expenses = self.transactions.filter(amount__lt=0).annotate(
            month=TruncMonth('date_of_transaction')
        ).values('month').annotate(
            monthly_sum=Sum("effective_amount")
        ).aggregate(
            avg_monthly_expenses=Avg('monthly_sum')
        )['avg_monthly_expenses'] or 0
        monthly_avg_incomes = self.transactions.filter(amount__gt=0).annotate(
            month=TruncMonth('date_of_transaction')
        ).values('month').annotate(
            monthly_sum=Sum("effective_amount")
        ).aggregate(
            avg_monthly_incomes=Avg('monthly_sum')
        )['avg_monthly_incomes'] or 0
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
            MONTHLY_AVG_NET: monthly_avg_net_str
        }

    def place_widget(self):
        if self.transactions:
            st.markdown(f'## Available')
            st.markdown(f'## :orange[TODO]')  # TODO: Add expenses

            col_1, col_2, col_3 = st.columns(3)
            with col_1:
                st.markdown(f'## Expenses')
                st.markdown(f'## :red[{self.stats.get(SUM_EXPENSES)}]')
                st.metric(label="Monthly averages:", value="", delta=self.stats.get(MONTHLY_AVG_EXPENSES))
            with col_2:
                st.markdown(f'## Sum of incomes')
                st.markdown(f'## :green[{self.stats.get(SUM_INCOMES)}]')
                st.metric(label="Sum of incomes", value="", delta=self.stats.get(MONTHLY_AVG_INCOMES), label_visibility="hidden")
            with col_3:
                st.markdown(f'## Net')
                st.markdown(f'## :blue[{self.stats.get(NET_SUM)}]')
                st.metric(label="Net value", value="", delta=self.stats.get(MONTHLY_AVG_NET), label_visibility="hidden")
