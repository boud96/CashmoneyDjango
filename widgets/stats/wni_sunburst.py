from django.db.models import QuerySet
from core.base.models import Transaction
from widgets.stats.base_widget import BaseWidget
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from constants import WidgetConstants


class TransactionWNIWidget(BaseWidget):
    def __init__(self, transactions: QuerySet[Transaction]):
        super().__init__(transactions)

    def preprocess_data(self):
        self.df["effective_amount"] = pd.to_numeric(
            self.df["effective_amount"], errors="coerce"
        )
        self.df = self.df.dropna(subset=["effective_amount"])

        self.df["want_need_investment"] = (
            self.df["want_need_investment"].fillna("None").astype(str).str.capitalize()
        )

    def create_wni_chart(self):
        # 1. Filter for Expenses
        filtered_df = self.df[self.df["effective_amount"] < 0].copy()
        filtered_df["effective_amount"] = filtered_df["effective_amount"].abs()

        if filtered_df.empty:
            return None

        # 2. Group Data
        grouped_df = filtered_df.groupby("want_need_investment", as_index=False)[
            "effective_amount"
        ].sum()

        # 3. Prepare Lists for Plotly
        labels = grouped_df["want_need_investment"].tolist()
        values = grouped_df["effective_amount"].tolist()
        colors = [WidgetConstants.WNI_COLORS.get(label, "#c8d6e5") for label in labels]

        # 4. Build Chart
        fig = go.Figure(
            go.Sunburst(
                labels=labels,
                parents=[""] * len(labels),
                values=values,
                branchvalues="total",
                marker=dict(colors=colors, line=dict(width=0)),
                textinfo="label+percent entry",
                hoverinfo="none",
                textfont=dict(color="#ffffff"),
            )
        )

        fig.update_layout(
            title=dict(text="Want / Need / Investment", x=0.5),
            margin=dict(t=40, l=0, r=0, b=0),
        )

        return fig

    def place_widget(self):
        if self.df.empty:
            st.info("No transactions found.")
            return

        self.preprocess_data()

        fig = self.create_wni_chart()

        if fig:
            st.plotly_chart(fig)
        else:
            st.info("No expense data found for W/N/I.")
