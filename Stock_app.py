import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# ================= PAGE CONFIG =================
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# ================= STYLES =================
plt.style.use('seaborn-v0_8-darkgrid')

st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #264653;
        color: #f4f4f4;
    }
    h1, h2, h3, h4 {
        color: #e9c46a;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# ✅ FIXED CONFIGURATION (THIS IS THE IMPORTANT PART)
# =========================================================
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()   # For Jupyter / Anaconda

STOCK_DATA_DIR = os.path.join(BASE_DIR, "stock_data_csvs")
SECTOR_DATA_PATH = os.path.join(BASE_DIR, "Sector_data - Sheet1.csv")

# ================= HARD FILE CHECK =================
if not os.path.exists(STOCK_DATA_DIR):
    st.error(f"""
❌ stock_data_csvs folder NOT FOUND

Expected location:
{STOCK_DATA_DIR}

➡ Run extract_data.py first
""")
    st.stop()

if not os.path.exists(SECTOR_DATA_PATH):
    st.error(f"""
❌ Sector_data - Sheet1.csv NOT FOUND

Expected location:
{SECTOR_DATA_PATH}

➡ Place the file in the same folder as app.py
""")
    st.stop()

# ================= FUNCTIONS =================
@st.cache_data
def load_all_stock_data(data_dir):
    all_data = []
    symbols = []

    for file in os.listdir(data_dir):
        if file.endswith(".csv"):
            symbol = file.replace(".csv", "")
            path = os.path.join(data_dir, file)

            df = pd.read_csv(path)
            df["Date"] = pd.to_datetime(df["Date"])
            df["Symbol"] = symbol

            all_data.append(df)
            symbols.append(symbol)

    master_df = pd.concat(all_data, ignore_index=True)
    master_df.drop_duplicates(subset=["Symbol", "Date"], inplace=True)

    return master_df, symbols


@st.cache_data
def load_sector_data(path):
    df = pd.read_csv(path)

    if "Symbol" not in df.columns:
        st.error("❌ 'Symbol' column missing in Sector CSV")
        st.stop()

    if "sector" not in df.columns:
        st.error("❌ 'sector' column missing in Sector CSV")
        st.stop()

    df["Extracted_Symbol"] = df["Symbol"].apply(
        lambda x: x.split(": ")[1] if isinstance(x, str) and ": " in x else x
    )

    df.drop_duplicates(subset=["Extracted_Symbol"], inplace=True)
    return df

# ================= UI =================
st.title("📊 Data-Driven Stock Analysis Dashboard")

# ================= LOAD DATA =================
with st.spinner("Loading stock data..."):
    master_df, stock_symbols = load_all_stock_data(STOCK_DATA_DIR)

with st.spinner("Loading sector data..."):
    sector_df = load_sector_data(SECTOR_DATA_PATH)

# ================= MERGE =================
master_df = pd.merge(
    master_df,
    sector_df[["Extracted_Symbol", "sector"]],
    left_on="Symbol",
    right_on="Extracted_Symbol",
    how="left"
)

master_df.rename(columns={"sector": "Sector"}, inplace=True)
master_df.drop(columns=["Extracted_Symbol"], inplace=True)

if master_df["Sector"].isnull().any():
    st.warning("⚠ Some stocks missing sector info")

st.success("✅ Data Loaded & Merged Successfully")
st.dataframe(master_df.head())

# ================= METRICS =================
st.header("📈 Key Performance Metrics")

master_df["Daily_Return"] = master_df.groupby("Symbol")["Close"].pct_change()

yearly_returns = {}
for symbol in stock_symbols:
    df = master_df[master_df["Symbol"] == symbol]
    if len(df) > 1:
        yearly_returns[symbol] = (
            (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]
        ) * 100

yearly_df = pd.DataFrame(yearly_returns.items(), columns=["Symbol", "Yearly_Return_Pct"])

st.subheader("Top 10 Green Stocks")
st.dataframe(yearly_df.sort_values(by="Yearly_Return_Pct", ascending=False).head(10))

st.subheader("Top 10 Red Stocks")
st.dataframe(yearly_df.sort_values(by="Yearly_Return_Pct").head(10))

# ================= VOLATILITY =================
st.header("📉 Volatility Analysis")

vol_df = master_df.groupby("Symbol")["Daily_Return"].std().reset_index(name="Volatility")
top_vol = vol_df.sort_values(by="Volatility", ascending=False).head(10)

fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(top_vol["Symbol"], top_vol["Volatility"])
ax.tick_params(axis="x", rotation=45)
ax.set_title("Top 10 Most Volatile Stocks")
st.pyplot(fig)

# ================= SECTOR PERFORMANCE =================
st.header("🏭 Sector-wise Performance")

sector_perf = pd.merge(
    yearly_df,
    master_df[["Symbol", "Sector"]].drop_duplicates(),
    on="Symbol"
)

sector_avg = sector_perf.groupby("Sector")["Yearly_Return_Pct"].mean().sort_values(ascending=False)

st.dataframe(sector_avg)

fig, ax = plt.subplots(figsize=(12, 6))
sector_avg.plot(kind="bar", ax=ax)
ax.tick_params(axis="x", rotation=45)
ax.set_title("Average Yearly Return by Sector")
st.pyplot(fig)

# ================= CORRELATION =================
st.header("🔗 Stock Correlation")

pivot = master_df.pivot(index="Date", columns="Symbol", values="Close")
corr = pivot.pct_change().corr()

fig, ax = plt.subplots(figsize=(14, 10))
sns.heatmap(corr, cmap="coolwarm", ax=ax)
st.pyplot(fig)

# ================= END =================
st.success("🎉 Dashboard Loaded Successfully – No Errors!")
