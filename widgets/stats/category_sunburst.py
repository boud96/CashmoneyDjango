import pandas as pd
import streamlit as st
import plotly.express as px


class TransactionSunburstWidget:
    def __init__(self, transactions_df: pd.DataFrame):
        self.transactions_df = transactions_df

    def preprocess_data(self):
        self.transactions_df['amount'] = pd.to_numeric(self.transactions_df['amount'], errors='coerce')
        self.transactions_df = self.transactions_df.dropna(subset=['amount'])

        self.transactions_df['category_name'] = self.transactions_df['category_name'].fillna("None")
        self.transactions_df['subcategory_name'] = self.transactions_df['subcategory_name'].fillna("None")

    def create_sunburst_charts(self):
        positive_df = self.transactions_df[self.transactions_df['amount'] > 0].reset_index(drop=True)
        negative_df = self.transactions_df[self.transactions_df['amount'] < 0].reset_index(drop=True)

        positive_df_grouped = positive_df.groupby(['category_name', 'subcategory_name'], as_index=False)['amount'].sum()
        negative_df_grouped = negative_df.groupby(['category_name', 'subcategory_name'], as_index=False)['amount'].sum()
        negative_df_grouped['amount'] = negative_df_grouped['amount'].abs()

        positive_colors = px.colors.qualitative.Prism  # TODO: Choose different scales, make it a settable constant?
        negative_colors = px.colors.qualitative.Safe

        positive_fig = None
        if not positive_df_grouped.empty:
            positive_fig = px.sunburst(
                positive_df_grouped,
                path=['category_name', 'subcategory_name'],
                values='amount',
                title="Incomes by Category",
                color='category_name',
                color_discrete_sequence=positive_colors,
            )

        negative_fig = None
        if not negative_df_grouped.empty:
            negative_fig = px.sunburst(
                negative_df_grouped,
                path=['category_name', 'subcategory_name'],
                values='amount',
                title="Expenses by Category",
                color='category_name',
                color_discrete_sequence=negative_colors,
            )

        return positive_fig, negative_fig

    def place_widget(self):
        if not self.transactions_df.empty:
            self.preprocess_data()
            positive_fig, negative_fig = self.create_sunburst_charts()

            col1, col2 = st.columns(2)
            with col1:
                if positive_fig is None:
                    st.info("No data to display")
                else:
                    st.plotly_chart(positive_fig)
            with col2:
                if negative_fig is None:
                    st.info("No data to display", )
                else:
                    st.plotly_chart(negative_fig)
