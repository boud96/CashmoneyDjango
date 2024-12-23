import os

import pandas as pd
import streamlit as st

from widgets.filters.category import CategoryFilter
from widgets.filters.date import DateFilter
from widgets.filters.manager import FilterManager

os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
import django

django.setup()
from core.base.models import Transaction, Category, Subcategory


from widgets.stats.overview_stats import OverviewStatsWidget


def main():
    st.set_page_config(
        page_title="Cashmoney", layout="wide", page_icon=""
    )
    st.title("Custom dashboard")

    # Initialize the FilterManager
    filter_manager = FilterManager()

    # Add DateFilter
    date_filter = DateFilter()
    filter_manager.add_filter("date", date_filter)

    # # Add CategoryFilter
    category_filter = CategoryFilter(Category, label="Select Categories")
    filter_manager.add_filter("category", category_filter)

    subcategory_filter = CategoryFilter(Subcategory, label="Select Subcategories")
    filter_manager.add_filter("subcategory", subcategory_filter)

    # Place all widgets in the sidebar
    filter_manager.place_widgets(sidebar=True)

    # Get combined filter params
    filter_params = filter_manager.get_combined_params()
    st.write("Combined Filter Parameters:", filter_params)




    transactions = Transaction.get_transactions_from_db(filter_params)

    overview_stats = OverviewStatsWidget(transactions)
    st.write(overview_stats.stats)
    overview_stats.place_widget()



    transactions_df = Transaction.get_transactions_as_dataframe(filter_params)
    st.write(transactions_df)


if __name__ == "__main__":
    main()


