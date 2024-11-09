import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
import django

django.setup()
from core.base.models import ImageAnnotation, Transaction


def get_annotations_from_db() -> pd.DataFrame:
    return pd.DataFrame.from_records(
        list(
            ImageAnnotation.objects.values(
                "label", "label_correctness", "image_correctness", "image_id"
            )
        )
    )

def get_transactions_from_db() -> pd.DataFrame:
    return pd.DataFrame.from_records(
        list(
            Transaction.objects.values(
                "date_of_transaction", "amount", "currency", "counterparty_name", "counterparty_note", "my_note", "other_note"
            )
        )
    )

def show_transactions(transactions_df: pd.DataFrame) -> None:
    st.subheader(f"Transactions")
    st.dataframe(transactions_df)
    st.write("---")


def show_header_metrics(annotations_df: pd.DataFrame) -> None:
    metric_columns = st.columns(3)
    metric_columns[0].metric(label="Annotations in DataBase", value=len(annotations_df))
    st.write("---")


def show_quality_metrics(annotations_df: pd.DataFrame, metric_name: str) -> None:
    st.subheader(f"{metric_name.replace('_', ' ')} metrics")
    metrics_df = annotations_df.pivot_table(
        columns=metric_name, index="label", values="image_id", aggfunc="count"
    )

    metric_columns = st.columns([1, 1, 2])

    # Metrics
    metric_columns[0].success(
        f"Label OK: {metrics_df['OK'].sum() if 'OK' in metrics_df else 0}"
    )
    metric_columns[0].warning(
        f"Label to Review: {metrics_df['TO_BE_CHECKED'].sum() if 'TO_BE_CHECKED' in metrics_df else 0}"
    )
    metric_columns[0].error(
        f"Label KO: {metrics_df['KO'].sum() if 'KO' in metrics_df else 0}"
    )

    # Plot
    fig, ax = plt.subplots()
    metrics_df.filter(items=["OK", "TO_BE_CHECKED", "KO"]).plot.bar(
        ax=ax, fontsize=15, alpha=0.5, grid=True, color=["green", "orange", "red"]
    )
    plt.legend(loc="upper left")
    metric_columns[2].pyplot(fig)
    plt.show()

    st.markdown("---")


def main():
    # Title
    st.set_page_config(
        page_title="Monitor Database Annotations", layout="wide", page_icon="📀"
    )
    st.title("Custom dashboard")

    # Get annotations from DB
    annotations_df = get_annotations_from_db()

    # Header metrics
    show_header_metrics(annotations_df)

    # Transactions
    transactions = get_transactions_from_db()
    show_transactions(transactions)


    # Correctness metrics
    show_quality_metrics(annotations_df, "label_correctness")
    show_quality_metrics(annotations_df, "image_correctness")


# %%
if __name__ == "__main__":
    main()
