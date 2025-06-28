import streamlit as st
from widgets.filters.base import BaseFilter


class ShowIgnoredFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.show_ignored = False

    def place_widget(self, sidebar=False):
        """
        Places the checkbox widget to toggle ignored transactions.
        :param sidebar: If True, places the widget in the sidebar, otherwise on the main page.
        """
        location = st.sidebar if sidebar else st
        location.header("Show Ignored Transactions:")
        self.show_ignored = location.checkbox(
            "Include ignored transactions?", value=False
        )

        # Update filter params to use 'show_ignored'
        self.set_param("show_ignored", self.show_ignored)
