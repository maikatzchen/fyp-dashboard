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

# TOMORROW.IO
TOMORROW_API_KEY = "plmRZoGH98gI1yHUVxzVzgPnvYTSauk7"
def get_tomorrowio_rainfall(lat, lon):
    try:
        url = "https://api.tomorrow.io/v4/timelines"
        params = {
            "location": f"{lat},{lon}",
            "fields": "precipitationAmount",
            "timesteps": "1d",
            "units": "metric",
            "startTime": "now",
            "endTime": "nowPlus3d",
            "apikey": TOMORROW_API_KEY
        }
        response = requests.get(url, params=params)
        data = response.json()

        intervals = data["data"]["timelines"][0]["intervals"]
        daily_rainfall = intervals[0]["values"]["precipitationAmount"]
        rainfall_3d = sum(i["values"]["precipitationAmount"] for i in intervals)

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
