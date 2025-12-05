from functools import cached_property
import pandas as pd
from django.db.models import QuerySet
import plotly.express as px
from pandas import DataFrame
from core.base.models import Transaction
from itertools import cycle


class BaseWidget:
    def __init__(self, transactions: QuerySet[Transaction] | list[str]):
        self.transactions = transactions

    @cached_property
    def df(self) -> DataFrame:
        """Convert the QuerySet to a DataFrame."""
        if not self.transactions.exists():
            return pd.DataFrame()
        data = pd.DataFrame.from_records(list(self.transactions.values()))
        return data

    @staticmethod
    def get_color_swatches():
        return (
            px.colors.qualitative.Prism
            + px.colors.qualitative.Vivid
            + px.colors.qualitative.Pastel
            + px.colors.qualitative.Safe
            + px.colors.qualitative.Bold
        )

    def get_category_color_map(self):
        """Create a consistent color mapping for categories"""
        cats = self.df["category_name"].fillna("Uncategorized").astype(str)
        unique_categories = sorted(cats.unique())

        swatches = self.get_color_swatches()
        color_cycle = cycle(swatches)

        color_map = {cat: next(color_cycle) for cat in unique_categories}
        return color_map

    def get_subcategory_color_map(self):
        """Create a consistent color mapping for subcategories"""
        subcats = self.df["subcategory_name"].fillna("Other").astype(str)
        unique_subcategories = sorted(subcats.unique())

        swatches = self.get_color_swatches()
        # Use a different offset or reversed list to try and distinguish from categories
        # (Optional, but helps visual distinction)
        color_cycle = cycle(swatches[::-1])

        color_map = {subcat: next(color_cycle) for subcat in unique_subcategories}
        return color_map
