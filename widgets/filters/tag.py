import streamlit as st
from widgets.filters.base import BaseFilter


class TagFilter(BaseFilter):
    def __init__(self, model, label: str):
        super().__init__()
        self.model = model
        self.label = label
        self.tags = self._fetch_tags()

    def _fetch_tags(self):
        tags = {"None": "None"}
        tags.update(
            {str(tag.id): tag.name for tag in self.model.objects.all().order_by("name")}
        )
        return tags

    def _update_selected(self):
        """Callback function to update session state when the pills selection changes."""
        selected = st.session_state.get("tag_filter")
        st.session_state["selected_tags"] = selected

    def _select_all(self):
        """Callback function to select all tags."""
        options = list(self.tags.values())
        st.session_state["selected_tags"] = options

    def _deselect_all(self):
        """Callback function to deselect all tags."""
        st.session_state["selected_tags"] = []

    def place_widget(self, sidebar=False):
        location = st.sidebar if sidebar else st
        options = list(self.tags.values())

        if "selected_tags" not in st.session_state:
            st.session_state["selected_tags"] = options

        with location.expander(f"{self.label}", expanded=True):
            selected = st.pills(
                f"Select {self.label}",
                options,
                selection_mode="multi",
                default=st.session_state["selected_tags"],
                key="tag_filter",
                on_change=self._update_selected,
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Select All",
                    key="select_all_tags",
                    on_click=self._select_all,
                ):
                    pass
            with col2:
                if st.button(
                    "Deselect All",
                    key="deselect_all_tags",
                    on_click=self._deselect_all,
                ):
                    pass

            selected_ids = [
                key for key, value in self.tags.items() if value in selected
            ]
            self.set_param("tag", selected_ids)
