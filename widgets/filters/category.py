import streamlit as st
from widgets.filters.base import BaseFilter


class CategoryFilter(BaseFilter):
    def __init__(self, model, label: str):
        super().__init__()
        self.model = model
        self.label = label
        self.categories = self._fetch_categories()

    def _fetch_categories(self):
        categories = {"None": "None"}
        categories.update(
            {str(category.id): category.name for category in self.model.objects.all().order_by("name")}
        )
        return categories

    def _update_selected(self):
        """Callback function to update session state when the pills selection changes."""
        selected = st.session_state.get(f"category_filter-{self.model.__name__}")
        st.session_state[f"selected_{self.model.__name__}"] = selected

    def _select_all(self):
        """Callback function to select all categories."""
        options = list(self.categories.values())
        st.session_state[f"selected_{self.model.__name__}"] = options

    def _deselect_all(self):
        """Callback function to deselect all categories."""
        st.session_state[f"selected_{self.model.__name__}"] = []

    def place_widget(self, sidebar=False):
        location = st.sidebar if sidebar else st
        options = list(self.categories.values())

        # Initialize session state for selection tracking if not already done
        if f"selected_{self.model.__name__}" not in st.session_state:
            st.session_state[f"selected_{self.model.__name__}"] = options

        with location.expander(f"{self.label}", expanded=True):
            selected = st.pills(
                f"Select {self.label}",
                options,
                selection_mode="multi",
                default=st.session_state[f"selected_{self.model.__name__}"],
                key=f"category_filter-{self.model.__name__}",
                on_change=self._update_selected,  # Register the callback
            )

            # Columns for select/deselect buttons inside the expander
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Select All", key=f"{self.model.__name__}_select_all", on_click =self._select_all):
                    pass  # The actual change will happen in the callback
            with col2:
                if st.button("Deselect All", key=f"{self.model.__name__}_deselect_all", on_click =self._deselect_all):
                    pass  # The actual change will happen in the callback

            # Map selected options back to category IDs
            selected_ids = [key for key, value in self.categories.items() if value in selected]
            self.set_param(self.model.__name__.lower(), selected_ids)
