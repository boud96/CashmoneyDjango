from widgets.filters.base import BaseFilter


class FilterManager:
    def __init__(self):
        """Initializes the manager with an empty dictionary of filters."""
        self.filters = {}

    def add_filter(self, key, filter_instance):
        """Adds a filter instance to the manager."""
        if not isinstance(filter_instance, BaseFilter):
            raise TypeError("Filter must be an instance of BaseFilter.")
        self.filters[key] = filter_instance

    def place_widgets(self, sidebar=False):
        """
        Places all filter widgets in the Streamlit app.
        :param sidebar: If True, places widgets in the sidebar, otherwise on the main page.
        """
        for filter_instance in self.filters.values():
            filter_instance.place_widget(sidebar=sidebar)

    def get_combined_params(self):
        """
        Combines the params from all filters into a single dictionary.
        :return: A dictionary of all filter params.
        """
        combined_params = {}
        for key, filter_instance in self.filters.items():
            combined_params.update(filter_instance.filter_params)
        return combined_params
