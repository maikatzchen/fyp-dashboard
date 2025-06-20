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

# District coordinates dictionary
district_coords = {
    "Besut": (5.79, 102.56),
    "Dungun": (4.75, 103.41),
    "Hulu Terengganu": (5.07, 103.01),
    "Kemaman": (4.23, 103.42),
    "Setiu": (5.52, 102.74)
}

# Get lat/lon based on selected district
lat, lon = district_coords[selected_district]



# Filter by selected date
filtered_df = df[df["date"] <= pd.to_datetime(selected_date)]

# Map of flood risk by location
st.subheader("🗺️ Flood Risk Map")
map_df = filtered_df[["lat", "lon", "rainfall_mm", "flood_label"]]
map_df["Flood Status"] = map_df["flood_label"].apply(lambda x: "Flood" if x == 1 else "No Flood")
fig_map = px.scatter_mapbox(map_df,
                            lat="lat",
                            lon="lon",
                            color="Flood Status",
                            size="rainfall_mm",
                            zoom=7,
                            height=500,
                            mapbox_style="open-street-map",
                            title="Flood Status Map")
fig_map.update_layout(mapbox=dict(zoom=7),
                      margin={"r":0,"t":40,"l":0,"b":0},
                      dragmode='zoom')
st.plotly_chart(fig_map, use_container_width=True)

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

# ==========================
# 🌧️ Real-Time Rainfall Section
# ==========================

st.subheader("🌦️ Real-Time Weather Inputs (Live)")

import requests

# Terengganu coordinates
lat, lon = 5.33, 103.14
api_key = "0ddef092786b6f1881790a638a583445"  # Replace with your API key

def get_openweather_rainfall(lat, lon, api_key):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    data = response.json()

    try:
        rainfall_mm = data["rain"]["1h"]  # Rainfall in mm over the last hour
    except KeyError:
        rainfall_mm = 0.0

    return rainfall_mm

# Call the function
rainfall_now = get_openweather_rainfall(lat, lon, api_key)

# Call GEE function
rainfall_3d = 85.3

col1, col2 = st.columns(2)

with col1:
    st.metric(label="🌧️ Hourly Rainfall (mm)", value=f"{rainfall_now:.2f}")

with col2:
    st.metric(label="📊 3-Day Rainfall Total (mm)", value=f"{rainfall_3d:.2f}")


# Show data table
with st.expander("🔍 Show Raw Data"):
    st.dataframe(filtered_df)
