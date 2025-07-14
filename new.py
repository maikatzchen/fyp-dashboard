# for testing purpose using IMERG and CHIRPS as fallback with error display for debugging 

import pandas as pd
import json
import streamlit as st
import requests
import datetime 
from datetime import date
import ee
import ast
from google.oauth2 import service_account
from google.cloud import aiplatform_v1
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from google.cloud.aiplatform_v1.types import PredictRequest
from google.cloud.aiplatform_v1.services.endpoint_service import EndpointServiceClient
from google.cloud.aiplatform_v1.services.model_service import ModelServiceClient
from google.cloud.aiplatform_v1.services.prediction_service import PredictionServiceClient

# === GCP AUTHENTICATION ===
service_account_info = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# === LOAD GEE CREDENTIALS FROM STREAMLIT SECRETS ===
def initialize_ee():
    ee.Initialize(credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"]))
initialize_ee()

# === FUNCTION: Get 1-hour rainfall from OpenWeatherMap ===

OPENWEATHER_API_KEY = st.secrets["openweather"]["api_key"]

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

        daily_precip = dataset.sum()
        result = daily_precip.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        
        rainfall = result_dict.get('precipitationCal', 0.0)

        # Use fallback if IMERG has 0.0
        if rainfall == 0.0:
            
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
        

        daily_precip = dataset.sum()
        result = daily_precip.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=5000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        
        return result_dict.get("precipitation", 0.0), "CHIRPS"

    except Exception as e:
        st.error(f"[CHIRPS Error] {e}")
        return 0.0
        
# === ADD: Get daily rainfall from Open-Meteo ===
def get_openmeteo_rainfall(lat, lon, start_date, end_date):
    """
    Get daily accumulated rainfall (mm) and 3-day accumulated rainfall (mm before selected_date) from Open-Meteo API
    """
    import datetime

    # Fetch 3 days before start_date up to selected_date
    start_date_api = start_date - datetime.timedelta(days=3)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "timezone": "Asia/Kuala_Lumpur",
        "start_date": start_date_api.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        st.error(f"[Open-Meteo API error] {response.status_code}: {response.text}")
        return None

    try:
        data = response.json()
        precipitation = data['daily']['precipitation_sum']
        dates = data['daily']['time']

        selected_date_str = start_date.strftime("%Y-%m-%d")

        if selected_date_str in dates:
            index = dates.index(selected_date_str)
            daily_rainfall = precipitation[index]

            # Get rainfall for 3 days before selected_date
            if index >= 3:
                rainfall_3d = sum(precipitation[index - 3:index])
            else:
                rainfall_3d = None  # Not enough data for 3-day accumulation

            return {
                "daily_rainfall": daily_rainfall,
                "rainfall_3d": rainfall_3d,
                "source": "Open-Meteo"
            }
        else:
            st.warning("⚠️ Open-Meteo returned no data for selected date.")
            return None
    except KeyError:
        st.warning("⚠️ Missing data in Open-Meteo response.")
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

# === Real-Time Weather Panel ===
st.subheader(f"🌇 Real-Time Weather Data for {selected_district}")

# === Sidebar Option ===
use_openmeteo = st.sidebar.checkbox("🌐 Use Open-Meteo API for Daily Rainfall?", value=False)

# Get real-time values
month = selected_date.month
rainfall_hour = get_openweather_rainfall(lat, lon)
if use_openmeteo:
    openmeteo_result = get_openmeteo_rainfall(lat, lon, selected_date, selected_date)
    if openmeteo_result:
        rainfall_day = openmeteo_result["daily_rainfall"]
        rainfall_3d = openmeteo_result["rainfall_3d"]  # Use Open-Meteo's 3-day rainfall
        source = openmeteo_result["source"]
    else:
        rainfall_day, source = get_daily_rainfall_gee(lat, lon, selected_date)
        rainfall_3d = get_gee_3day_rainfall(lat, lon, selected_date)
else:
    rainfall_day, source = get_daily_rainfall_gee(lat, lon, selected_date)
    rainfall_3d = get_gee_3day_rainfall(lat, lon, selected_date)

col1, col2 = st.columns(2)
# col3.metric("Current Rainfall (mm)", f"{rainfall_hour:.2f}")
col1.metric(f"Rainfall (mm) [{source}]", f"{rainfall_day:.2f}")
col2.metric(
    "3-Day Rainfall (mm)",
    f"{rainfall_3d:.2f}" if rainfall_3d is not None else "N/A"
)


# === Optional Map (showing location) ===
df = pd.DataFrame({"lat": [lat], "lon": [lon]})
st.map(df)

if st.button("Predict Flood Risk"):
    with st.spinner("Predicting flood risk..."):
        result = get_flood_prediction(month, rainfall_day, rainfall_3d)

        result_dict = dict(result)
        st.write("📦 Raw Prediction Response (dict):", result_dict)

        classes_raw = result_dict.get("classes", "[]")
        scores_raw = result_dict.get("scores", "[]")

        if isinstance(classes_raw, str):
            try:
                classes = json.loads(classes_raw.replace("'", '"'))
            except json.JSONDecodeError:
                st.error("❌ Failed to parse 'classes'. Check model response.")
                st.write("🔎 Raw 'classes':", classes_raw)
                classes = []
        else:
            classes = classes_raw

        # Ensure scores is a list
        if isinstance(scores_raw, str):
            try:
                scores = json.loads(scores_raw.replace("'", '"'))
            except json.JSONDecodeError:
                st.error("❌ Failed to parse 'scores'. Check model response.")
                st.write("🔎 Raw 'scores':", scores_raw)
                scores = []
        else:
            scores = scores_raw

        # If we got valid classes and scores
        if classes and scores:
            if '1' in classes:
                flood_index = classes.index('1')
                flood_prob = float(scores[flood_index])
                no_flood_prob = 1 - flood_prob

                flood_percent = round(flood_prob * 100, 2)
                no_flood_percent = round(no_flood_prob * 100, 2)

                st.write(f"🌊 **Flood Probability:** {flood_percent}%")
                st.write(f"☀️ **No Flood Probability:** {no_flood_percent}%")

                predicted_class = "Flood" if flood_prob >= no_flood_prob else "No Flood"

                if predicted_class == "Flood":
                    st.error(f"🚨 **Predicted: {predicted_class}**")
                else:
                    st.success(f"✅ **Predicted: {predicted_class}**")
            else:
                st.error("❌ Class '1' (Flood) not found in model response.")
                st.write("🔎 Classes:", classes)
        else:
            st.error("❌ Prediction response missing scores or classes.")

