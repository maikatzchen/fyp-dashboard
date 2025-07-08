# for testing purpose using IMERG and CHIRPS as fallback with error display for debugging 

import pandas as pd
import json
import streamlit as st
import requests
import datetime 
from datetime import date
import ee
from google.oauth2 import service_account
from google.cloud import aiplatform

# === GCP AUTHENTICATION ===
service_account_info = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(service_account_info)
aiplatform.init(project="pivotal-crawler-459812-m5", location="us-east1", credentials=credentials)

# === LOAD GEE CREDENTIALS FROM STREAMLIT SECRETS ===
def initialize_ee():
    ee.Initialize(credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"]))
initialize_ee()

# === CONFIGURATION ===
OPENWEATHER_API_KEY = st.secrets["openweather"]["api_key"]

# === FUNCTION: Get 1-hour rainfall from OpenWeatherMap ===
def get_openweather_rainfall(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    response = requests.get(url, params=params)
    data = response.json()
    try:
        return data["rain"].get("1h", 0.0)
    except:
        return 0.0

# === FUNCTION: Get 3-day rainfall from GEE ===
def get_gee_3day_rainfall(lat, lon, end_date):
    try:
        start_date = end_date - datetime.timedelta(days=3)
        region = ee.Geometry.Point(lon, lat).buffer(10000)  # ✅ 10 km buffer

        dataset = ee.ImageCollection("NASA/GPM_L3/IMERG_V06") \
            .filterDate(str(start_date), str(end_date)) \
            .select("precipitationCal")

        rainfall_image = dataset.sum()
        result = rainfall_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        rainfall = result_dict.get("precipitationCal", 0.0)

        if rainfall == 0.0:
            st.warning("IMERG 3-day rainfall is 0.0 or unavailable. Switching to CHIRPS backup...")
            return get_3day_rainfall_chirps(lat, lon, end_date)

        return rainfall

    except Exception as e:
        st.error(f"[GEE Error - IMERG 3-Day] {e}")
        return get_3day_rainfall_chirps(lat, lon, end_date)


# === BACKUP: Get 3-day rainfall from CHIRPS ===
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

# === FUNCTION: Get Daily rainfall from GEE ===
def get_daily_rainfall_gee(lat, lon, date_input):
    try:
        if isinstance(date_input, datetime.date):
            date_obj = datetime.datetime.combine(date_input, datetime.time())
        else:
            date_obj = datetime.datetime.strptime(date_input, '%Y-%m-%d')

        start_date = ee.Date(date_obj.strftime('%Y-%m-%d'))
        end_date = start_date.advance(1, 'day')
        region = ee.Geometry.Point([lon, lat]).buffer(10000)  # ✅ 10 km buffer

        dataset = (
            ee.ImageCollection("NASA/GPM_L3/IMERG_V06")
            .filterDate(start_date, end_date)
            .select('precipitationCal')
        )

        image_count = dataset.size().getInfo()
        st.write(f"IMERG image count for {date_obj.date()}: {image_count}")

        daily_precip = dataset.sum()
        result = daily_precip.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        st.write("Daily result (raw):", result_dict)
        rainfall = result_dict.get('precipitationCal', 0.0)

        # Use fallback if IMERG has 0.0
        if rainfall == 0.0:
            st.warning("IMERG daily rainfall is 0.0 or unavailable. Switching to CHIRPS backup...")
            return get_daily_rainfall_chirps(lat, lon, date_input)  # ✅ returns tuple (value, source)

        return rainfall, "IMERG"

    except Exception as e:
        st.error(f"[GEE Error] {e}")
        st.warning("Switching to CHIRPS as fallback...")
        return get_daily_rainfall_chirps(lat, lon, date_input)

# === BACKUP: Get Daily rainfall from CHIRPS ===
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
        st.error(f"[CHIRPS Error] {e}")
        return 0.0

# === CALL VERTEX AI PREDICTION ===
def get_flood_prediction(month, rainfall_mm, rainfall_3d):
    endpoint = aiplatform.Endpoint("8324160641333985280")

    instances = [{
        "month": int(month),
        "rainfall_mm": float(rainfall_mm),
        "rainfall_3d": float(rainfall_3d)
    }]
    
#DEBUG PURPOSE: PRINT PAYLOAD
    st.write("Vertex AI Payload:", instances)
    payload = {"instances": instances}
    prediction = endpoint.predict(instances=payload["instances"])
    
# DEBUT PURPOSE: PRINT RAW PREDICTION RESPONSE
    st.write("Vertex AI Response:", prediction)
    return prediction[0]

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

# === Real-Time Weather Panel ===
st.subheader(f"🌇 Real-Time Weather Data for {selected_district}")

# Get real-time values
month = st.number_input("Month (1-12)", min_value=1, max_value=12, value=7)
rainfall_hour = get_openweather_rainfall(lat, lon)
rainfall_day, source = get_daily_rainfall_gee(lat, lon, selected_date)
rainfall_3d = get_gee_3day_rainfall(lat, lon, selected_date)

col1, col2, col3 = st.columns(3)
col1.metric("Current Rainfall (mm)", f"{rainfall_hour:.2f}")
col2.metric(f"Rainfall (mm) [{source}]", f"{rainfall_day:.2f}")
col3.metric("3-Day Rainfall (mm)", f"{rainfall_3d:.2f}")

# === Optional Map (showing location) ===
df = pd.DataFrame({"lat": [lat], "lon": [lon]})
st.map(df)

if st.button("Predict Flood Risk"):
    result = get_flood_prediction(month, rainfall_day, rainfall_3d)
    st.write("🌊 Flood Probability:", round(result["flood_label_1_scores"] * 100, 2), "%")
    st.write("✅ No Flood Probability:", round(result["flood_label_0_scores"] * 100, 2), "%")
