# app.py
# Using CHIRPS for satellite fallback + Data.gov.my API for local forecasts

import streamlit as st
import requests
import datetime
from datetime import date
import time
from functools import lru_cache
import ee
from google.oauth2 import service_account
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# TOMORROW.IO
TOMORROW_API_KEY = st.secrets["tomorrowio"]["api_key"]
def get_tomorrowio_rainfall(lat, lon):
    try:
        url = "https://api.tomorrow.io/v4/timelines"
        headers = {
            "accept": "application/json",
            "apikey": TOMORROW_API_KEY
        }
        # Format ISO8601 timestamps
        now = datetime.datetime.utcnow()
        start_time = now.isoformat() + "Z"
        end_time = (now + datetime.timedelta(days=3)).isoformat() + "Z"

        payload = {
            "location": f"{lat},{lon}",
            "fields": ["precipitationIntensity"],
            "units": "metric",
            "timesteps": ["1d"],
            "startTime": "star_time",
            "endTime": end_time,
            "timezone": "auto"  # Required
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        st.write("Tomorrow.io raw response:", response.json())

        timelines = data.get("data", {}).get("timelines", [])
        if not timelines:
            st.warning("No timelines data found.")
            return 0.0, 0.0

        intervals = timelines[0].get("intervals", [])
        if not intervals:
            st.warning("No intervals data found.")
            return 0.0, 0.0

        daily_rainfall = intervals[0]["values"].get("precipitationAmount", 0.0)
        rainfall_3d = sum(i["values"].get("precipitationAmount", 0.0) for i in intervals)

        return daily_rainfall, rainfall_3d

    except Exception as e:
        st.error(f"[Tomorrow.io Error] {e}")
        return 0.0, 0.0
        
# === STREAMLIT UI ===
st.set_page_config(page_title="Flood Prediction Dashboard", layout="wide")
st.title("🌧️ Flood Prediction Dashboard")

# === District filter ===
st.sidebar.header("Filters")
districts = {
    "Besut": (5.79, 102.56),
    "Dungun": (4.75, 103.41),
    "Hulu Terengganu": (5.07, 103.01),
    "Kemaman": (4.23, 103.42),
    "Setiu": (5.52, 102.74)
}
selected_date = st.sidebar.date_input("Select a date", datetime.date.today())
selected_district = st.sidebar.selectbox("Select a district", list(districts.keys()))
lat, lon = districts[selected_district]

# Get rainfall data
rainfall_daily, rainfall_3d = get_tomorrowio_rainfall(lat, lon)


col1, col2 = st.columns(2)
col1.metric("🌧️ Daily Rainfall (Tomorrow.io)", f"{rainfall_daily:.2f} mm")
col2.metric("🌧️ 3-Day Rainfall (Tomorrow.io)", f"{rainfall_3d:.2f} mm")


# === Optional Map (showing location) ===
st.map(data={"lat": [lat], "lon": [lon]})
