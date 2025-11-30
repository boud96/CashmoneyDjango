import streamlit as st
from widgets.filters.base import BaseFilter


class CategoryFilter(BaseFilter):
    def __init__(self, model, label: str):
        super().__init__()
        self.model = model
        self.label = label
        self.categories = self._fetch_categories()
        self.widget_key = f"category_filter-{self.model.__name__}"

    def _fetch_categories(self):
        categories = {"None": "None"}
        categories.update(
            {
                str(category.id): category.name
                for category in self.model.objects.all().order_by("name")
            }
        )
        return categories

    def place_widget(self, sidebar=False):
        location = st.sidebar if sidebar else st
        options = list(self.categories.values())

        if self.widget_key not in st.session_state:
            st.session_state[self.widget_key] = options

        with location.expander(f"{self.label}", expanded=True):
            selected = st.pills(
                f"Select {self.label}",
                options,
                selection_mode="multi",
                key=self.widget_key,
            )

            col1, col2 = st.columns(2)
            with col1:
                st.button(
                    "Select All",
                    key=f"{self.model.__name__}_select_all",
                    on_click=self.select_all,
                    args=(self.widget_key, options),
                )
            with col2:
                st.button(
                    "Deselect All",
                    key=f"{self.model.__name__}_deselect_all",
                    on_click=self.deselect_all,
                    args=(self.widget_key,),
                )

            selected_ids = [
                key for key, value in self.categories.items() if value in selected
            ]
            self.set_param(self.model.__name__.lower(), selected_ids)
