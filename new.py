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
        # Use forecast API (better for free plan)
        url = "https://api.tomorrow.io/v4/weather/realtime"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {TOMORROW_API_KEY}"
        }
        params = {
            "location": f"{lat},{lon}"
        }

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        st.write("Tomorrow.io raw response:", data)

        # Extract daily forecasts
        daily_data = data.get("timelines", {}).get("daily", [])
        if not daily_data:
            st.warning("No daily forecast data found.")
            return 0.0, 0.0

        # Get daily precipitation amount
        daily_rainfall = daily_data[0]["values"].get("precipitationAmount", 0.0)

        # Sum up 3-day rainfall
        rainfall_3d = sum(
            day["values"].get("precipitationAmount", 0.0)
            for day in daily_data[:3]
        )

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
