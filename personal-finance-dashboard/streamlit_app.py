import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO

st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")
st.title("📊 Personal Finance Dashboard (UPI-Based)")

# File upload
uploaded_file = st.file_uploader("Upload your bank statement CSV", type="csv")

if uploaded_file:
    raw_lines = uploaded_file.read().decode("utf-8").splitlines()

    # Try to auto-detect header
    header_index = None
    for i, line in enumerate(raw_lines):
        if "Date" in line and "Remarks" in line:
            header_index = i
            break

    if header_index is not None:
        df = pd.read_csv(StringIO("\n".join(raw_lines[header_index:])))

        # Drop last row if it's mostly empty
        if df.tail(1).isnull().sum().sum() > 2:
            df = df[:-1]

        # Extract name from UPI remark
        def extract_name(remark):
            try:
                parts = str(remark).split("/")
                return parts[3] if len(parts) > 3 else remark
            except:
                return "Unknown"

        df["Name"] = df["Remarks"].apply(extract_name)

        # Load known mappings
        try:
            known_map = pd.read_csv("known_recipients.csv")
        except:
            known_map = pd.DataFrame(columns=["Name", "Category"])

        df = df.merge(known_map, on="Name", how="left")
        df["Category"].fillna("Uncategorized", inplace=True)

        # Assign categories to unknowns
        st.subheader("📝 Assign Categories to New Names")
        uncategorized = df[df["Category"] == "Uncategorized"]["Name"].unique()

        new_entries = []
        categories = known_map["Category"].unique().tolist() if not known_map.empty else []

        for name in uncategorized:
            cat = st.text_input(f"Enter category for: {name}", key=name)
            if cat:
                if cat not in categories:
                    categories.append(cat)
                new_entries.append({"Name": name, "Category": cat})
                df.loc[df["Name"] == name, "Category"] = cat

        if st.button("✅ Save Category Mapping"):
            new_df = pd.DataFrame(new_entries)
            updated_map = pd.concat([known_map, new_df], ignore_index=True).drop_duplicates("Name")
            updated_map.to_csv("known_recipients.csv", index=False)
            st.success("Mappings saved to known_recipients.csv")

        # Categorized transactions
        st.subheader("📋 Categorized Transactions")
        st.dataframe(df[["Date", "Name", "Debit", "Category"]])

        # Spending by category
        st.subheader("📊 Spending by Category")
        spend = df.groupby("Category")["Debit"].sum().sort_values(ascending=False)
        fig, ax = plt.subplots()
        sns.barplot(x=spend.index, y=spend.values, ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

        # Monthly Trends
        st.subheader("📈 Monthly Trends")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
        df = df.dropna(subset=["Date"])
        df["Month"] = df["Date"].dt.to_period("M")
        pivot = df.pivot_table(index="Month", columns="Category", values="Debit", aggfunc="sum")
        st.bar_chart(pivot.fillna(0))

    else:
        st.error("❌ Could not find valid header in uploaded file.")
