import streamlit as st
from widgets.filters.base import BaseFilter


class RecalculateAmountsByOwnersFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.recalculate_by_owners = False

    def place_widget(self, sidebar=False):
        """
        Places the checkbox widget to recalculate amounts based on the number of owners.
        :param sidebar: If True, places the widget in the sidebar, otherwise on the main page.
        """
        location = st.sidebar if sidebar else st
        location.header("Recalculate Amounts by Owners:")
        self.recalculate_by_owners = location.checkbox("By number ow owners", value=False)

        # Update filter params to use 'recalculate_by_owners'
        self.set_param("recalculate_by_owners", self.recalculate_by_owners)
