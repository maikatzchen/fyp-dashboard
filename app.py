import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Page setup
st.set_page_config(page_title="Terengganu Flood Prediction Dashboard", layout="wide")
st.title("🌧️ Terengganu Flood Prediction Dashboard")

# Sidebar filters
st.sidebar.header("Filters")
selected_date = st.sidebar.date_input("Select a date", datetime(2021, 12, 1))
selected_district = st.sidebar.selectbox("Select a district", ["Besut", "Dungun", "Hulu Terengganu", "Kemaman", "Setiu"])

# Mock data (replace this with your actual dataset later)
data = {
    "date": pd.date_range(start="2021-11-01", periods=30, freq='D'),
    "rainfall_mm": [round(abs(i*1.3 % 70), 2) for i in range(30)],
    "rainfall_3d": [round(abs(i*2.4 % 150), 2) for i in range(30)],
    "flood_label": [1 if i % 7 == 0 else 0 for i in range(30)],
    "district": [selected_district]*30
}
df = pd.DataFrame(data)

# Filter by selected date
filtered_df = df[df["date"] <= pd.to_datetime(selected_date)]

# Rainfall chart
st.subheader(f"📈 Rainfall Trends in {selected_district} (Last 30 Days)")
fig = px.line(filtered_df, x="date", y=["rainfall_mm", "rainfall_3d"],
              labels={"value": "Rainfall (mm)", "date": "Date"},
              title="Daily vs 3-Day Accumulated Rainfall")
st.plotly_chart(fig, use_container_width=True)

# Flood risk prediction (mocked)
st.subheader("🚨 Flood Risk Prediction")
latest = filtered_df.iloc[-1]

st.metric(label="Selected Date", value=selected_date.strftime('%Y-%m-%d'))
st.metric(label="Rainfall (mm)", value=latest["rainfall_mm"])
st.metric(label="3-Day Accumulated Rainfall", value=latest["rainfall_3d"])

flood_risk = "Flood Likely" if latest["flood_label"] == 1 else "No Flood"
st.markdown(f"### Predicted Status: **{flood_risk}**")

# Show data table
with st.expander("🔍 Show Raw Data"):
    st.dataframe(filtered_df)
