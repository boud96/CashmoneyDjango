import streamlit as st
from django.db.models import Count

from core.base.models import Transaction

st.header("TODO: Warnings like")
st.write("Detected duplicates by same original ID")
st.write("Uncategorized transactions")
st.write("Mark warned transaction as OK")


# Step 1: Find duplicates grouped by the specified fields
duplicates = (
    Transaction.objects.values("amount", "original_id", "counterparty_note")
    .annotate(count=Count("id"))
    .filter(count__gt=1)
)

# Step 2: Fetch and print details for each duplicate group
if duplicates:
    st.write("Duplicate transactions found:\n")
    for duplicate in duplicates:
        st.write(
            f"Amount: {duplicate['amount']}, "
            # f"Date of Submission: {duplicate['date_of_submission']}, "
            # f"Date of Transaction: {duplicate['date_of_transaction']}, "
            f"Original ID: {duplicate['original_id']}, "
            f"Count: {duplicate['count']}"
        )

        # Query to fetch the full records matching this duplicate group
        duplicate_records = Transaction.objects.filter(
            amount=duplicate["amount"],
            original_id=duplicate["original_id"],
        ).values("id", "bank_account", "my_note", "other_note")

        # Print details for each duplicate record
        for record in duplicate_records:
            st.write(record)
        st.divider()  # Add a newline for better readability
else:
    print("No duplicates found.")
