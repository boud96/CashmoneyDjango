import streamlit as st
from app import app_launcher

from widgets.recategorize import recategorize_tab_widget
from widgets.csv_import import import_form_widget
from widgets.filters.bank_account import BankAccountFilter
from widgets.filters.by_owners import RecalculateAmountsByOwnersFilter
from widgets.filters.category import CategoryFilter
from widgets.filters.date import DateFilter
from widgets.filters.tag import TagFilter
from widgets.filters.ignored import ShowIgnoredFilter
from widgets.filters.manager import FilterManager
from widgets.stats.bar_chart import BarChartWidget
from widgets.stats.dataframe import DataFrameWidget
from widgets.stats.category_sunburst import TransactionSunburstWidget
from widgets.stats.wni_sunburst import TransactionWNIWidget
from widgets.stats.overview_stats import OverviewStatsWidget


def main():
    models = app_launcher.get_models()
    Transaction = models[
        "Transaction"
    ]  # TODO: Refactor as models_transaction introduce in the app object
    Category = models["Category"]
    Subcategory = models["Subcategory"]
    BankAccount = models["BankAccount"]
    Tag = models["Tag"]

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
    recalculate_by_owners_filter = RecalculateAmountsByOwnersFilter()
    filter_manager.add_filter("recalculate_by_owners", recalculate_by_owners_filter)

    # Add BankAccountFilter  # TODO: Remove None?
    bank_account_filter = BankAccountFilter(BankAccount, label="Select Bank Accounts")
    filter_manager.add_filter("bank_account", bank_account_filter)

    tag_filter = TagFilter(Tag, label="Select Tags")
    filter_manager.add_filter("tag", tag_filter)

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

    home_tab, recategorize_tab, import_tab = st.tabs(["Home", "Recategorize", "Import"])
    with home_tab:
        # Overview Stats
        overview_stats = OverviewStatsWidget(transactions, filter_params)
        overview_stats.place_widget()

        # Bar Chart
        bar_chart = BarChartWidget(transactions, filter_params)
        bar_chart.place_widget()

        # Sun Bursts
        transaction_sunburst = TransactionSunburstWidget(transactions)
        transaction_sunburst.place_widget()

        widget = TransactionWNIWidget(transactions)
        widget.place_widget()

    with recategorize_tab:
        recategorize_tab_widget(transactions)

    with import_tab:
        import_form_widget()

    # DataFrame
    transactions_dataframe = DataFrameWidget(transactions)
    transactions_dataframe.place_widget()


if __name__ == "__main__":
    main()
