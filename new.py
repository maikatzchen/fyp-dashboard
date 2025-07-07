# app.py
# Using CHIRPS for satellite fallback + Data.gov.my API for local forecasts

import streamlit as st
import requests
import datetime
from datetime import date
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

# === FUNCTION: Get rainfall chance from Data.gov.my ===
@st.cache_data(ttl=600)
def get_datagovmy_rainfall(location):
    try:
        url = "https://api.data.gov.my/weather/forecast"
        params = {"location__location_name": location, "limit": 1}
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            forecast = data["data"][0]["forecast"][0]
            rain_chance = forecast.get("chance_of_rain", 0)
            return rain_chance
        else:
            st.warning(f"data.gov.my API returned {resp.status_code}")
            return None
    except Exception as e:
        st.error(f"[Data.gov.my Error] {e}")
        return None

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

# === Get data ===
rainfall_govmy = get_datagovmy_rainfall(selected_district)
rainfall_daily, source_daily = get_daily_rainfall_chirps(lat, lon, selected_date)
rainfall_3d = get_3day_rainfall_chirps(lat, lon, selected_date)

# === Display metrics ===
col1, col2, col3 = st.columns(3)
if rainfall_govmy is not None:
    col1.metric("☔ Rain Chance (Data.gov.my)", f"{rainfall_govmy}%")
else:
    col1.metric("☔ Rain Chance (Data.gov.my)", "N/A")

col2.metric(f"📅 Daily Rainfall ({source_daily})", f"{rainfall_daily:.2f} mm")
col3.metric("🌧️ 3-Day Rainfall (CHIRPS)", f"{rainfall_3d:.2f} mm")

# === Optional Map (showing location) ===
st.map(data={"lat": [lat], "lon": [lon]})
