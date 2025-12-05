import streamlit as st
from widgets.filters.base import BaseFilter


class TagFilter(BaseFilter):
    def __init__(self, model, label: str):
        super().__init__()
        self.model = model
        self.label = label
        self.tags = self._fetch_tags()
        self.widget_key = "tag_filter"

    def _fetch_tags(self):
        tags = {"None": "None"}
        tags.update(
            {str(tag.id): tag.name for tag in self.model.objects.all().order_by("name")}
        )
        return tags

    def place_widget(self, sidebar=False):
        location = st.sidebar if sidebar else st
        options = list(self.tags.values())

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
                    key="select_all_tags",
                    on_click=self.select_all,
                    args=(self.widget_key, options),
                )
            with col2:
                st.button(
                    "Deselect All",
                    key="deselect_all_tags",
                    on_click=self.deselect_all,
                    args=(self.widget_key,),
                )

            selected_ids = [
                key for key, value in self.tags.items() if value in selected
            ]
            self.set_param("tag", selected_ids)
