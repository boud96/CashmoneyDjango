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
        data_categories = {}

        queryset = self.model.objects.all().order_by("name")

        try:
            self.model._meta.get_field("category")
            queryset = queryset.select_related("category")
        except Exception:
            pass

        for item in queryset:
            parent = getattr(item, "category", None)

            if parent and hasattr(parent, "name") and parent.name:
                label = f"{parent.name} - {item.name}"
            else:
                label = item.name

            data_categories[str(item.id)] = label

        sorted_data = dict(
            sorted(data_categories.items(), key=lambda item: item[1].lower())
        )

        categories = {"None": "None"}
        categories.update(sorted_data)

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
                width="stretch",
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
