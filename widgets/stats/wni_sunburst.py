from django.db.models import QuerySet

from widgets.stats.base_widget import BaseWidget
import pandas as pd
import streamlit as st
import plotly.express as px


class TransactionWNIWidget(BaseWidget):
    def __init__(self, transactions: QuerySet):
        super().__init__(transactions)

    def preprocess_data(self):
        self.df["effective_amount"] = pd.to_numeric(self.df["effective_amount"], errors='coerce')
        self.df = self.df.dropna(subset=["effective_amount"])

        # Handle missing values in the 'want_need_investment' field
        self.df['want_need_investment'] = self.df['want_need_investment'].fillna("None")

    def create_sunburst_chart(self):
        filtered_df = self.df[self.df["effective_amount"] < 0].copy()
        filtered_df["effective_amount"] = filtered_df["effective_amount"].abs()

        grouped_df = filtered_df.groupby('want_need_investment', as_index=False)["effective_amount"].sum()

        total_amount = grouped_df["effective_amount"].sum()
        grouped_df['percentage'] = (grouped_df["effective_amount"] / total_amount * 100).round(2)
        grouped_df['label'] = grouped_df.apply(
            lambda row: f"{row['want_need_investment']} ({row['percentage']}%)", axis=1
        )

        fig = px.sunburst(
            grouped_df,
            path=['label'],
            values="effective_amount",
            title="Want-Need-Investment",
            color='want_need_investment',
            color_discrete_sequence=px.colors.qualitative.Set2  # TODO: Change color scheme as constants
        )

        return fig

    def place_widget(self):
        if not self.df.empty:
            self.preprocess_data()
            fig = self.create_sunburst_chart()
            st.plotly_chart(fig)