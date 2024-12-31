from datetime import datetime

from widgets.filters.base import BaseFilter

import streamlit as st


class DateFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.date_from = None
        self.date_to = None

    def place_widget(self, sidebar=False):
        """
        Places the date range widget.
        :param sidebar: If True, places the widget in the sidebar, otherwise on the main page.
        """
        location = st.sidebar if sidebar else st
        location.header("Select a Date Range:")
        self.date_from = location.date_input("From", value=None)
        self.date_to = location.date_input("To", value=None)

        # Update filter params
        self.set_param("date_from", self.date_from)
        self.set_param("date_to", self.date_to)
