# app.py

import streamlit as st
import requests
import datetime 
from datetime import date
import ee
from google.oauth2 import service_account

# === LOAD GEE CREDENTIALS FROM STREAMLIT SECRETS ===
def initialize_ee():
    service_account_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(service_account_info,
    scopes=["https://www.googleapis.com/auth/cloud-platform"])
    ee.Initialize(credentials)
initialize_ee()

# === CONFIGURATION ===
OPENWEATHER_API_KEY = "0ddef092786b6f1881790a638a583445"  

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
    start_date = end_date - datetime.timedelta(days=3)
    region = ee.Geometry.Point(lon, lat).buffer(10000)  # ✅ 10 km buffer
    dataset = ee.ImageCollection("NASA/GPM_L3/IMERG_V06") \
        .filterDate(str(start_date), str(end_date)) \
        .select("precipitationCal")
    rainfall_image = dataset.sum()
    rainfall_mm = rainfall_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=10000,
        maxPixels=1e9
    ).get("precipitationCal")
    try:
        return rainfall_mm.getInfo()
    except:
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

        # Debug image count
        image_count = dataset.size().getInfo()
        st.write(f"IMERG image count for {date_obj.date()}: {image_count}")

        # Aggregate rainfall
        daily_precip = dataset.sum()

        result = daily_precip.reduceRegion(
            reducer=ee.Reducer.mean(),  # Optional: use .sum() if you want total mm over the area
            geometry=region,
            scale=10000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        st.write("Daily result (raw):", result_dict)

        return result_dict.get('precipitationCal', 0.0)

    except Exception as e:
        st.error(f"[GEE Error] {e}")
        return 0.0



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
rainfall_mm = get_openweather_rainfall(lat, lon)
rainfall_daily = get_daily_rainfall_gee(lat,lon, selected_date)
rainfall_3d = get_gee_3day_rainfall(lat, lon, selected_date)

col1, col2, col3 = st.columns(3)
col1.metric("Today's Hourly Rainfall (mm)", f"{rainfall_mm:.2f}")
col2.metric("3-Day Rainfall (mm)", f"{rainfall_3d:.2f}")
col3.metric("Today's Rainfall (mm)", f"{rainfall_daily:.2f}")

# === Optional Map (showing location) ===
st.map(data={"lat": [lat], "lon": [lon]})
