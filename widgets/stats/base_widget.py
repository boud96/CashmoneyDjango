from functools import cached_property
import pandas as pd
from django.db.models import QuerySet
import plotly.express as px
from pandas import DataFrame

from core.base.models import Transaction


class BaseWidget:
    def __init__(self, transactions: QuerySet[Transaction] | list[str]):
        self.transactions = transactions

    @cached_property
    def df(self) -> DataFrame:
        """Convert the QuerySet to a DataFrame."""
        if not self.transactions.exists():
            return pd.DataFrame()

        data = pd.DataFrame.from_records(self.transactions.values())
        return data

    @staticmethod
    def get_color_swatches():
        return (
            px.colors.qualitative.Prism
            + px.colors.qualitative.Vivid
            + px.colors.qualitative.Pastel
            + px.colors.qualitative.Safe
        )

    def get_category_color_map(self):
        """Create a consistent color mapping for categories"""
        unique_categories = sorted(self.df["category_name"].unique())
        swatches = self.get_color_swatches()
        color_map = {cat: color for cat, color in zip(unique_categories, swatches)}
        if "None" in color_map:
            color_map["None"] = "#808080"
        return color_map

    def get_subcategory_color_map(self):
        # TODO: Reuse the get_category_color_map
        """Create a consistent color mapping for subcategories"""
        unique_subcategories = sorted(self.df["subcategory_name"].unique())
        swatches = self.get_color_swatches()
        color_map = {
            subcat: color for subcat, color in zip(unique_subcategories, swatches)
        }
        if "None" in color_map:
            color_map["None"] = "#808080"
        return color_map
