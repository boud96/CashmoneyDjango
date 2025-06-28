from datetime import datetime, timedelta
import streamlit as st
from widgets.filters.base import BaseFilter


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

        today = datetime.today()
        default_date_from = today - timedelta(days=2 * 365)  # Roughly two years ago
        default_date_to = today

        self.date_from = location.date_input("From", value=default_date_from.date())
        self.date_to = location.date_input("To", value=default_date_to.date())

        self.set_param("date_from", self.date_from)
        self.set_param("date_to", self.date_to)
