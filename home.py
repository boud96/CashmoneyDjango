import os

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from widgets.filters.bank_account import BankAccountFilter
from widgets.filters.by_owners import RecalculateAmountsByOwnersFilter
from widgets.filters.category import CategoryFilter
from widgets.filters.date import DateFilter
from widgets.filters.ignored import ShowIgnoredFilter
from widgets.filters.manager import FilterManager
from widgets.stats.bar_chart import BarChartWidget
from widgets.stats.dataframe import DataFrameWidget
from widgets.stats.category_sunburst import TransactionSunburstWidget
from widgets.stats.wni_sunburst import TransactionWNIWidget

os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
import django

django.setup()
from core.base.models import Transaction, Category, Subcategory, BankAccount

from widgets.stats.overview_stats import OverviewStatsWidget


def main():
    st.set_page_config(page_title="Cashmoney", layout="wide", page_icon="")

    # Initialize the FilterManager
    filter_manager = FilterManager()

    # Add DateFilter
    date_filter = DateFilter()
    filter_manager.add_filter("date", date_filter)

    # Add CategoryFilter
    category_filter = CategoryFilter(Category, label="Select Categories")
    filter_manager.add_filter("category", category_filter)

    # Add SubcategoryFilter
    subcategory_filter = CategoryFilter(Subcategory, label="Select Subcategories")
    filter_manager.add_filter("subcategory", subcategory_filter)

    # Add ShowIgnoredFilter
    show_ignored_filter = ShowIgnoredFilter()
    filter_manager.add_filter("show_ignored", show_ignored_filter)

    # Add RecalculateAmountsByOwnersFilter
    recalculate_by_owners_filter = RecalculateAmountsByOwnersFilter()  # TODO: Work in progress?
    filter_manager.add_filter("recalculate_by_owners", recalculate_by_owners_filter)

    # Add BankAccountFilter  # TODO: Remove None?
    bank_account_filter = BankAccountFilter(BankAccount, label="Select Bank Accounts")
    filter_manager.add_filter("bank_account", bank_account_filter)

    # Place all widgets in the sidebar
    filter_manager.place_widgets(sidebar=True)

    # Get combined filter params
    filter_params = filter_manager.get_combined_params()
    st.write("Combined Filter Parameters:")  # TODO: Remove - debug
    st.json(filter_params, expanded=False)

    transactions = Transaction.get_transactions_from_db(filter_params)
    if not transactions:
        st.info("No transactions found.")
        return

    # Overview Stats
    overview_stats = OverviewStatsWidget(transactions)
    overview_stats.place_widget()

    # Bar Chart
    bar_chart = BarChartWidget(transactions)
    bar_chart.place_widget()

    # DataFrame
    transactions_dataframe = DataFrameWidget(transactions)
    transactions_dataframe.place_widget()

    transactions_df = Transaction.get_transactions_as_dataframe(filter_params)  # TODO: This won't be needed, make SunburstWidget use transactions directly
    transaction_sunburst = TransactionSunburstWidget(transactions_df)
    transaction_sunburst.place_widget()


    widget = TransactionWNIWidget(transactions_df)
    widget.place_widget()


if __name__ == "__main__":
    main()
