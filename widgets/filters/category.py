import streamlit as st

from widgets.filters.base import BaseFilter


class CategoryFilter(BaseFilter):
    def __init__(self, model, label: str):
        """
        Initializes the CategoryFilter.
        :param model: Django model to fetch categories from.
        :param label: Label to display in the Streamlit widget.
        """
        super().__init__()
        self.model = model
        self.label = label
        self.categories = self._fetch_categories()

    def _fetch_categories(self):
        """Fetches categories from the database and prepares a dictionary."""
        categories = {"None": "None"}
        categories.update(
            {str(category.id): category.name for category in self.model.objects.all().order_by("name")}
        )
        return categories

    def place_widget(self, sidebar=False):
        """
        Places the category selection widget.
        :param sidebar: If True, places the widget in the sidebar, otherwise on the main page.
        """
        location = st.sidebar if sidebar else st
        options = self.categories.values()

        selection = location.pills(
            self.label,
            options,
            selection_mode="multi",
            default=options,
            key=f"category_filter-{self.model.__name__}",
        )

        # Map selected options back to category IDs
        selected_ids = [key for key, value in self.categories.items() if value in selection]
        self.set_param("categories", selected_ids)
