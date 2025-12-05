import streamlit as st


class BaseFilter:
    def __init__(self):
        self.filter_params = {}

    def set_param(self, key, value):
        """Sets a filter parameter key-value pair."""
        self.filter_params[key] = value

    def get_param(self, key):
        """Gets the value of a specific filter parameter."""
        return self.filter_params.get(key)

    def clear_params(self):
        """Clears all filter parameters."""
        self.filter_params.clear()

    def select_all(self, widget_key, all_options):
        """
        Generic callback to select all items.
        Args:
            widget_key (str): The st.session_state key for the widget.
            all_options (list): The list of all available options to select.
        """
        st.session_state[widget_key] = all_options

    def deselect_all(self, widget_key):
        """
        Generic callback to deselect all items.
        Args:
            widget_key (str): The st.session_state key for the widget.
        """
        st.session_state[widget_key] = []
