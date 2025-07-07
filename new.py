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

# === LOAD GEE CREDENTIALS FROM STREAMLIT SECRETS ===
def initialize_ee():
    service_account_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    ee.Initialize(credentials)
initialize_ee()

# === FUNCTION: Get 3-day rainfall from CHIRPS ===
def get_3day_rainfall_chirps(lat, lon, end_date):
    try:
        start_date = end_date - datetime.timedelta(days=3)
        region = ee.Geometry.Point(lon, lat).buffer(10000)

        dataset = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
            .filterDate(str(start_date), str(end_date)) \
            .select("precipitation")

        rainfall_image = dataset.sum()
        result = rainfall_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=5000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        st.write("CHIRPS 3-day result (raw):", result_dict)
        return result_dict.get("precipitation", 0.0)
    except Exception as e:
        st.error(f"[CHIRPS Error - 3-Day] {e}")
        return 0.0

# === FUNCTION: Get Daily rainfall from CHIRPS ===
def get_daily_rainfall_chirps(lat, lon, date_input):
    try:
        if isinstance(date_input, datetime.date):
            date_obj = datetime.datetime.combine(date_input, datetime.time())
        else:
            date_obj = datetime.datetime.strptime(date_input, '%Y-%m-%d')

        start_date = ee.Date(date_obj.strftime('%Y-%m-%d'))
        end_date = start_date.advance(1, 'day')
        region = ee.Geometry.Point([lon, lat]).buffer(10000)

        dataset = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
            .filterDate(start_date, end_date) \
            .select("precipitation")
        
        image_count = dataset.size().getInfo()
        st.write(f"CHIRPS image count for {date_obj.date()}: {image_count}")

        daily_precip = dataset.sum()
        result = daily_precip.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=5000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        st.write("CHIRPS daily result (raw):", result_dict)
        return result_dict.get("precipitation", 0.0), "CHIRPS"

    except Exception as e:
        st.error(f"[CHIRPS Error - Daily] {e}")
        return 0.0, "Unavailable"

# DATA.GOV.MY
@st.cache_data(ttl=600)  # Cache API result for 10 minutes
def get_rainfall_datagovmy(location, end_date):
    url = "https://api.data.gov.my/weather/forecast"
    params = {"location__location_name": location, "limit": 1}

    response = fetch_with_retry(url, params)
    if response is None:
        return None, None

    try:
        data = response.json()
        if not data or "data" not in data[0]:
            st.warning(f"No forecast data for {location}.")
            return None, None

        forecasts = data[0].get("forecast", [])
        daily_rainfall = None
        three_day_rainfall = 0.0

        for forecast in forecasts:
            forecast_date = datetime.datetime.strptime(forecast["forecast_date"], "%Y-%m-%d").date()

            # Daily rainfall for selected date
            if forecast_date == end_date:
                daily_rainfall = forecast.get("rainfall", 0.0)

            # Sum rainfall for the last 3 days
            if end_date - datetime.timedelta(days=3) < forecast_date <= end_date:
                three_day_rainfall += forecast.get("rainfall", 0.0)

        return daily_rainfall, three_day_rainfall

    except Exception as e:
        st.error(f"[Data.gov.my Parsing Error] {e}")
        return None, None


        
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
rainfall_daily, rainfall_3d = get_rainfall_datagovmy(selected_district, selected_date)


col1, col2 = st.columns(2)
col1.metric("📅 Daily Rainfall (data.gov.my)", f"{rainfall_daily:.2f} mm" if rainfall_daily else "N/A")
col2.metric("🌧️ 3-Day Rainfall (data.gov.my)", f"{rainfall_3d:.2f} mm" if rainfall_3d else "N/A")


# === Optional Map (showing location) ===
st.map(data={"lat": [lat], "lon": [lon]})
