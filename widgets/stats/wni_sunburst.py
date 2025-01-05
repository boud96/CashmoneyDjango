import pandas as pd
import streamlit as st
import plotly.express as px


class TransactionWNIWidget:
    def __init__(self, transactions_df: pd.DataFrame):
        self.transactions_df = transactions_df

    def preprocess_data(self):
        self.transactions_df['amount'] = pd.to_numeric(self.transactions_df['amount'], errors='coerce')
        self.transactions_df = self.transactions_df.dropna(subset=['amount'])

        # Handle missing values in the 'want_need_investment' field
        self.transactions_df['want_need_investment'] = self.transactions_df['want_need_investment'].fillna("None")

    def create_sunburst_chart(self):
        filtered_df = self.transactions_df[self.transactions_df['amount'] < 0].copy()
        filtered_df['amount'] = filtered_df['amount'].abs()

        grouped_df = filtered_df.groupby('want_need_investment', as_index=False)['amount'].sum()

        total_amount = grouped_df['amount'].sum()
        grouped_df['percentage'] = (grouped_df['amount'] / total_amount * 100).round(2)
        grouped_df['label'] = grouped_df.apply(
            lambda row: f"{row['want_need_investment']} ({row['percentage']}%)", axis=1
        )

        fig = px.sunburst(
            grouped_df,
            path=['label'],
            values='amount',
            title="Want-Need-Investment",
            color='want_need_investment',
            color_discrete_sequence=px.colors.qualitative.Set2  # TODO: Change color scheme as constants
        )

        return fig

    def place_widget(self):
        if not self.transactions_df.empty:
            self.preprocess_data()
            fig = self.create_sunburst_chart()
            st.plotly_chart(fig)
