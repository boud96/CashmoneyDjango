import pandas as pd
import streamlit as st
from django.db.models import QuerySet

from constants import WidgetConstants
from core.base.models import Transaction
from widgets.stats.base_widget import BaseWidget


class DataFrameWidget(BaseWidget):
    DATE_COL = "date_of_transaction"
    ACCOUNT_COL = "account_name"
    CATEGORY_COL = "category_name"
    SUBCATEGORY_COL = "subcategory_name"
    COUNTERPARTY_COL = "counterparty_name"
    COUNTERPARTY_NOTE_COL = "counterparty_note"
    MY_NOTE_COL = "my_note"
    OTHER_NOTE_COL = "other_note"
    AMOUNT_COL = "effective_amount"
    TAGS_COL = "tags"
    WANT_NEED_INVESTMENT_COL = "want_need_investment"

    COLUMN_DISPLAY_NAMES = {
        DATE_COL: "Date",
        ACCOUNT_COL: "Account",
        CATEGORY_COL: "Category",
        SUBCATEGORY_COL: "Subcategory",
        COUNTERPARTY_COL: "Counterparty",
        COUNTERPARTY_NOTE_COL: "Counterparty Note",
        MY_NOTE_COL: "My Note",
        OTHER_NOTE_COL: "Other Note",
        AMOUNT_COL: "Amount",
        TAGS_COL: "Tags",
        WANT_NEED_INVESTMENT_COL: "W / N / I",
    }

    def __init__(self, transactions: QuerySet[Transaction]):
        super().__init__(transactions)

    def _name_colors(self, column_name):
        """
        Assign unique colors based on the internal column name.
        """
        if column_name == self.CATEGORY_COL:
            return self.get_category_color_map()

        elif column_name == self.SUBCATEGORY_COL:
            return self.get_subcategory_color_map()

        # NEW: Check for W/N/I column
        elif column_name == self.WANT_NEED_INVESTMENT_COL:
            return WidgetConstants.WNI_COLORS

        else:
            # Fallback for other columns (Account, Tags, etc.)
            unique_values = self.df[column_name].fillna("None").unique()
            unique_values = sorted(unique_values)
            swatches = self.get_color_swatches()
            color_map = {value: color for value, color in zip(unique_values, swatches)}
            color_map[None] = "#808080"
            color_map["None"] = "#808080"
            return color_map

    def _style_names(self, val, column_name):
        """
        Apply background colors using the appropriate color map.
        """
        colors = self._name_colors(column_name)

        lookup_val = val

        # Handle Missing / Null values standardly
        if val is None or val == "None" or pd.isna(val):
            if column_name == self.CATEGORY_COL:
                lookup_val = "Uncategorized"
            elif column_name == self.SUBCATEGORY_COL:
                lookup_val = "Other"
            elif column_name == self.WANT_NEED_INVESTMENT_COL:
                lookup_val = "None"
            else:
                lookup_val = "None"

        if column_name == self.WANT_NEED_INVESTMENT_COL and isinstance(lookup_val, str):
            lookup_val = lookup_val.capitalize()

        bg_color = colors.get(lookup_val, "")
        return f"background-color: {bg_color}"

    @staticmethod
    def _style_amount(val):
        if pd.isna(val):
            return ""
        color = "green" if val > 0 else "red"
        return f"color: {color}"

    def _get_ordered_and_renamed_df(self):
        # 1. Define Order
        columns = [
            self.DATE_COL,
            self.CATEGORY_COL,
            self.SUBCATEGORY_COL,
            self.ACCOUNT_COL,
            self.WANT_NEED_INVESTMENT_COL,
            self.AMOUNT_COL,
            self.TAGS_COL,
            self.COUNTERPARTY_COL,
            self.COUNTERPARTY_NOTE_COL,
            self.MY_NOTE_COL,
            self.OTHER_NOTE_COL,
        ]

        # 2. Filter existing columns
        existing_cols = [col for col in columns if col in self.df.columns]

        # 3. Create copy
        display_df = self.df[existing_cols].copy()

        # 4. Rename
        display_df = display_df.rename(columns=self.COLUMN_DISPLAY_NAMES)

        return display_df

    def _create_styled_dataframe(self, display_df):
        def get_disp(col_name):
            return self.COLUMN_DISPLAY_NAMES.get(col_name, col_name)

        styler = display_df.style

        # 1. Account
        if self.ACCOUNT_COL in self.df.columns:
            styler = styler.map(
                lambda val: self._style_names(val, self.ACCOUNT_COL),
                subset=[get_disp(self.ACCOUNT_COL)],
            )

        # 2. Category
        if self.CATEGORY_COL in self.df.columns:
            styler = styler.map(
                lambda val: self._style_names(val, self.CATEGORY_COL),
                subset=[get_disp(self.CATEGORY_COL)],
            )

        # 3. Subcategory
        if self.SUBCATEGORY_COL in self.df.columns:
            styler = styler.map(
                lambda val: self._style_names(val, self.SUBCATEGORY_COL),
                subset=[get_disp(self.SUBCATEGORY_COL)],
            )

        # 4. Want/Need/Investment
        if self.WANT_NEED_INVESTMENT_COL in self.df.columns:
            styler = styler.map(
                lambda val: self._style_names(val, self.WANT_NEED_INVESTMENT_COL),
                subset=[get_disp(self.WANT_NEED_INVESTMENT_COL)],
            )

        # 5. Amount
        if self.AMOUNT_COL in self.df.columns:
            styler = styler.map(self._style_amount, subset=[get_disp(self.AMOUNT_COL)])

        styler = styler.format(
            {
                get_disp(self.AMOUNT_COL): "{:.2f}",
                get_disp(self.DATE_COL): lambda x: x.strftime("%Y-%m-%d")
                if not pd.isnull(x)
                else "",
            }
        )

        return styler

    def place_widget(self):
        if self.df.empty:
            st.info("No transactions found.")
            return

        display_df = self._get_ordered_and_renamed_df()
        styled_df = self._create_styled_dataframe(display_df)

        st.dataframe(styled_df, hide_index=True)
