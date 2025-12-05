from django.db.models import QuerySet
from widgets.stats.base_widget import BaseWidget
import pandas as pd
import streamlit as st
import plotly.graph_objects as go  # <--- Switched to graph_objects


class TransactionSunburstWidget(BaseWidget):
    def __init__(self, transactions: QuerySet):
        super().__init__(transactions)

    def preprocess_data(self):
        self.df["effective_amount"] = pd.to_numeric(
            self.df["effective_amount"], errors="coerce"
        )
        self.df = self.df.dropna(subset=["effective_amount"])

        # Fill NaNs so our logic doesn't break
        self.df["category_name"] = self.df["category_name"].fillna("Uncategorized")
        self.df["subcategory_name"] = self.df["subcategory_name"].fillna("Other")

    def _build_sunburst_figure(self, df_subset, title, cat_color_map, subcat_color_map):
        """
        Manually builds the Parents, Labels, IDs, and Colors lists
        required for go.Sunburst.
        """
        if df_subset.empty:
            return None

        # 1. Aggregate Data
        # Group by Category + Subcategory
        grouped = df_subset.groupby(
            ["category_name", "subcategory_name"], as_index=False
        )["effective_amount"].sum()

        # Calculate Category Totals (for the inner ring)
        cat_totals = grouped.groupby("category_name", as_index=False)[
            "effective_amount"
        ].sum()

        # --- ARRAYS FOR PLOTLY ---
        ids = []
        labels = []
        parents = []
        values = []
        colors = []

        # 2. Build Inner Ring (Categories)
        for _, row in cat_totals.iterrows():
            cat = row["category_name"]
            val = row["effective_amount"]

            ids.append(cat)  # Unique ID: "Food"
            labels.append(cat)  # Label: "Food"
            parents.append("")  # Parent: Root (empty)
            values.append(val)
            # Assign color from category map
            colors.append(cat_color_map.get(cat, "#808080"))

        # 3. Build Outer Ring (Subcategories)
        for _, row in grouped.iterrows():
            cat = row["category_name"]
            subcat = row["subcategory_name"]
            val = row["effective_amount"]

            # ID must be unique. "Other" might exist in "Food" AND "Transport".
            # So ID = "Food - Other", Label = "Other"
            unique_id = f"{cat} - {subcat}"

            ids.append(unique_id)
            labels.append(subcat)
            parents.append(cat)  # Parent is the Category
            values.append(val)
            # Assign color from subcategory map
            colors.append(subcat_color_map.get(subcat, "#808080"))

        # 4. Create Plot
        fig = go.Figure(
            go.Sunburst(
                ids=ids,
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker=dict(colors=colors, line=dict(width=0)),
                textinfo="label+value+percent entry",
                hoverinfo="none",
                textfont=dict(color="#ffffff"),
            )
        )

        fig.update_layout(
            title=dict(text=title, x=0.5),  # Center title
            margin=dict(t=40, l=0, r=0, b=0),
        )
        return fig

    def create_sunburst_charts(self):
        # Prepare Data
        positive_df = self.df[self.df["effective_amount"] > 0].copy()
        negative_df = self.df[self.df["effective_amount"] < 0].copy()

        # Make expenses positive for visualization
        negative_df["effective_amount"] = negative_df["effective_amount"].abs()

        # Get Color Maps
        cat_map = self.get_category_color_map()
        subcat_map = self.get_subcategory_color_map()

        # Build Charts
        pos_fig = self._build_sunburst_figure(
            positive_df, "Incomes", cat_map, subcat_map
        )
        neg_fig = self._build_sunburst_figure(
            negative_df, "Expenses", cat_map, subcat_map
        )

        return pos_fig, neg_fig

    def place_widget(self):
        if self.df.empty:
            st.info("No transactions found.")
            return

        self.preprocess_data()

        if self.df.empty:
            st.info("No valid transaction data to display.")
            return

        positive_fig, negative_fig = self.create_sunburst_charts()

        col1, col2 = st.columns(2)
        with col1:
            if positive_fig:
                st.plotly_chart(positive_fig)
            else:
                st.info("No Income Data")

        with col2:
            if negative_fig:
                st.plotly_chart(negative_fig)
            else:
                st.info("No Expense Data")
