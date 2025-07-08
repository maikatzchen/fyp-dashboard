# for testing purpose using IMERG and CHIRPS as fallback with error display for debugging 

import pandas as pd
import json
import streamlit as st
import requests
import datetime 
from datetime import date
import ee
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

# === AUTO-DETECT MODEL SCHEMA & CALL PREDICTION ===
def get_flood_prediction(month, rainfall_mm, rainfall_3d):
    client_options = {"api_endpoint": "us-east1-aiplatform.googleapis.com"}
    
    # Initialize Vertex AI clients
    endpoint_client = EndpointServiceClient(
    credentials=credentials,
    client_options=client_options
)
    model_client = ModelServiceClient(
    credentials=credentials,
    client_options=client_options
)
    prediction_client = PredictionServiceClient(
    credentials=credentials,
    client_options=client_options
)

    # Get deployed model info
    project = "pivotal-crawler-459812-m5"
    endpoint_id = "8324160641333985280"
    location = "us-east1"
    endpoint_name = f"projects/{project}/locations/{location}/endpoints/{endpoint_id}"

    endpoint = endpoint_client.get_endpoint(name=endpoint_name)
    deployed_model = endpoint.deployed_models[0]  # Assuming only 1 deployed model

    st.write("🔍 Model Display Name:", deployed_model.display_name)
    st.write("🔍 Model Resource Name:", deployed_model.model)

    # Get model details (schema)
    model = model_client.get_model(name=deployed_model.model)
    st.write("📦 Model Full Metadata:", model)

    # Show user what fields the model expects
    st.success("✅ Auto-detected model schema. Check above for details.")
    
    # === PREPARE PREDICTION PAYLOAD ===
    # You may need to adjust field names here based on schema
    instance_dict = {
        "month": str(month),
        "rainfall_mm": str(rainfall_mm),
        "rainfall_3d": str(rainfall_3d)
    }
    instances = [instance_dict]

    # DEBUG: Show payload before sending
    st.write("🚀 Payload being sent to Vertex AI:", instances)

    # Call prediction
    response = prediction_client.predict(
        endpoint=endpoint_name,
        instances=instances
    )

    st.write("🎯 Vertex AI Response:", response)
    predictions = response.predictions
    if predictions:
        st.success(f"✅ Prediction Result: {predictions[0]}")
        return predictions[0]
    else:
        st.error("❌ No predictions returned.")
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

# Get real-time values
month = selected_date.month
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

no_flood_prob = result.get("flood_label_0_scores", 0)
flood_prob = result.get("flood_label_1_scores", 0)
no_flood_percent = round(no_flood_prob * 100, 2)
flood_percent = round(flood_prob * 100, 2)

if st.button("Predict Flood Risk"):
    result = get_flood_prediction(month, rainfall_day, rainfall_3d)
    st.write(f"🌊 **Flood Probability:** {flood_percent}%")
    st.write(f"☀️ **No Flood Probability:** {no_flood_percent}%")

predicted_class = "Flood" if flood_prob >= no_flood_prob else "No Flood"
if predicted_class == "Flood":
    st.error(f"🚨 **Predicted: {predicted_class}**")
else:
    st.success(f"✅ **Predicted: {predicted_class}**")
