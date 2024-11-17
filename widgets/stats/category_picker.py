import streamlit as st

class CategoryPickerWidget:
    def __init__(self, model, label: str): # TODO: type hint model
        self.model = model
        self.label = label
        self.categories = {"None": "None"}
        self.categories.update(
            {str(category.id): category.name for category in self.model.objects.all().order_by("name")})

    def place_widget(self):
        options = self.categories.values()
        selection = st.pills(self.label, options, selection_mode="multi", default=options,
                             key=f"category_picker-{self.model.__name__}")
        selected_ids = [key for key, value in self.categories.items() if value in selection]
        selected_info = {ctg_id: self.categories[ctg_id] for ctg_id in selected_ids}

        return selected_info