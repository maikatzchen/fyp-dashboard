import os
import pandas as pd
import json
import streamlit as st
import requests
import datetime
from datetime import date
import ee
import folium
from streamlit_folium import st_folium
from google.oauth2 import service_account
from google.cloud import aiplatform_v1
from google.cloud.aiplatform_v1.types import PredictRequest
from google.cloud.aiplatform_v1.services.endpoint_service import EndpointServiceClient
from google.cloud.aiplatform_v1.services.model_service import ModelServiceClient
from google.cloud.aiplatform_v1.services.prediction_service import PredictionServiceClient
from google.cloud import secretmanager
import firebase_admin
from firebase_admin import credentials as firebase_credentials, firestore
import smtplib
from email.mime.text import MIMEText
import plotly.graph_objects as go

# === GCP AUTHENTICATION ===
def access_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    project_id = "pivotal-crawler-459812-m5"
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")
    return payload

service_account_info = json.loads(access_secret("gcp_service_account"))
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# === LOAD GEE AND VERTEX AI ===
import urllib3

# Patch TrafficPolice to avoid connection deadlocks
if hasattr(urllib3, "util") and hasattr(urllib3.util, "traffic_police"):
    urllib3.util.traffic_police._enabled = False

@st.cache_resource
def initialize_ee():
    ee.Initialize(credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"]))

initialize_ee()

@st.cache_resource
def get_vertex_ai_clients():
    client_options = {"api_endpoint": "us-east1-aiplatform.googleapis.com"}
    endpoint_client = EndpointServiceClient(credentials=credentials, client_options=client_options)
    model_client = ModelServiceClient(credentials=credentials, client_options=client_options)
    prediction_client = PredictionServiceClient(credentials=credentials, client_options=client_options)
    return endpoint_client, model_client, prediction_client

endpoint_client, model_client, prediction_client = get_vertex_ai_clients()

# === PRIMARY: Get daily rainfall from Open-Meteo ===
@st.cache_data(ttl=3600)
def get_openmeteo_rainfall(lat, lon, start_date, end_date, suppress_warnings=False):
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
        if not suppress_warnings:
            st.warning(f"Open-Meteo provides data only 7 days in the past and up to 16 days in the future. Switching to IMERG/CHIRPS historical data...")
        return None

    try:
        data = response.json()
        precipitation = data['daily']['precipitation_sum']
        dates = data['daily']['time']

        selected_date_str = start_date.strftime("%Y-%m-%d")

        if selected_date_str in dates:
            index = dates.index(selected_date_str)
            daily_rainfall = precipitation[index] or 0.0

            # Get rainfall for 3 days before selected_date
            if index >= 3:
                rainfall_3d = sum(p or 0 for p in precipitation[index - 3:index])
            else:
                rainfall_3d = sum(p or 0 for p in precipitation[:index])

            return {
                "daily_rainfall": daily_rainfall,
                "rainfall_3d": rainfall_3d,
                "source": "Open-Meteo"
            }
        else:
            st.warning("⚠️ Open-Meteo returned no data for selected date.")
            return None
    except KeyError:
        if not suppress_warnings:
            st.warning("⚠️ Missing data in Open-Meteo response. Falling back to CHIRPS...")
        return None

# === BACKUP: Get Daily rainfall from GEE ===
@st.cache_data(ttl=3600)
def get_daily_rainfall_gee(lat, lon, date_input, suppress_warnings=False):
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
            return get_daily_rainfall_chirps(lat, lon, date_input, suppress_warnings)  # ✅ returns tuple (value, source)
        return rainfall, "IMERG"
    except Exception as e:
        return get_daily_rainfall_chirps(lat, lon, date_input, suppress_warnings)

# === BACKUP: Get Daily rainfall from CHIRPS ===
@st.cache_data(ttl=3600)
def get_daily_rainfall_chirps(lat, lon, date_input, suppress_warnings=False):
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
            scale=10000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
    
        return result_dict.get("precipitation", 0.0), "CHIRPS"
    except Exception as e:
        return 0.0, "CHIRPS"
        
# === BACKUP: Get 3-day rainfall from GEE ===
@st.cache_data(ttl=3600)
def get_gee_3day_rainfall(lat, lon, end_date, suppress_warnings=False):
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
            
            return get_3day_rainfall_chirps(lat, lon, end_date, suppress_warnings)
        return rainfall, "IMERG"
    except Exception as e:
        return get_3day_rainfall_chirps(lat, lon, end_date, suppress_warnings)


# === BACKUP: Get 3-day rainfall from CHIRPS ===
@st.cache_data(ttl=3600)
def get_3day_rainfall_chirps(lat, lon, end_date, suppress_warnings=False):
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
            scale=10000,
            maxPixels=1e9
        )

        result_dict = result.getInfo()
        
        return result_dict.get("precipitation", 0.0), "CHIRPS"
    except Exception as e:
        return 0.0, "CHIRPS"


# === VERTEX AI === auto-detect model and call prediction
def get_flood_prediction(month, rainfall_mm, rainfall_3d):
    # Use cached clients
    global endpoint_client, model_client, prediction_client

    # Get deployed model info
    project = "pivotal-crawler-459812-m5"
    endpoint_id = "4787005346499526656"
    location = "us-east1"
    endpoint_name = f"projects/{project}/locations/{location}/endpoints/{endpoint_id}"

    endpoint = endpoint_client.get_endpoint(name=endpoint_name)
    deployed_model = endpoint.deployed_models[0]

    # Get model details (schema)
    model = model_client.get_model(name=deployed_model.model)
    
    # === PREPARE PREDICTION PAYLOAD ===
    instance_dict = {
        "month": str(month),
        "rainfall_mm": str(rainfall_mm),
        "rainfall_3d": str(rainfall_3d)
    }
    instances = [instance_dict]

    # Call prediction
    response = prediction_client.predict(
        endpoint=endpoint_name,
        instances=instances
    )

    predictions = response.predictions
    if predictions:
        return predictions[0]
    else:
        st.error("❌ No predictions returned.")
        return None

# === FIRESTORE ===
if not firebase_admin._apps:
    firebase_creds = json.loads(access_secret("FIREBASE_CREDENTIALS"))

    # Convert to plain dict if needed
    if not isinstance(firebase_creds, dict):
        import json
        firebase_creds = json.loads(firebase_creds)
    else:
        firebase_creds = dict(firebase_creds)

    cred = firebase_credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

SUBSCRIBERS_COLLECTION = "subscribers"


# === GMAIL CONFIG ===
GMAIL_USER = access_secret("GMAIL_USER")
GMAIL_APP_PASSWORD = access_secret("GMAIL_APP_PASSWORD")

def add_subscriber(email):
    doc_ref = db.collection(SUBSCRIBERS_COLLECTION).document(email)
    if doc_ref.get().exists:
        return False
    doc_ref.set({"email": email, "subscribed_at": firestore.SERVER_TIMESTAMP})
    return True

def remove_subscriber(email):
    doc_ref = db.collection(SUBSCRIBERS_COLLECTION).document(email)
    if doc_ref.get().exists:
        doc_ref.delete()
        return True
    return False

def load_subscribers():
    docs = db.collection(SUBSCRIBERS_COLLECTION).stream()
    return [doc.id for doc in docs]

def send_email_smtp(subject, message_html, to_email):
    """Send email using Gmail SMTP."""
    msg = MIMEText(message_html, 'html')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = to_email

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [to_email], msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")


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
# Try Open-Meteo first
openmeteo = get_openmeteo_rainfall(lat, lon, selected_date, selected_date)
if openmeteo:
    rainfall_day = openmeteo["daily_rainfall"]
    rainfall_3d = openmeteo["rainfall_3d"]
    source = "Open-Meteo API"
else:
    # Directly call IMERG, no fallback inside
    imerg_value, imerg_source = get_daily_rainfall_gee(lat, lon, selected_date)
    rainfall_day = imerg_value
    source = imerg_source

    rainfall_3d, _ = get_gee_3day_rainfall(lat, lon, selected_date)

    # If still 0.0, fallback directly to CHIRPS
    if rainfall_day == 0.0:
        rainfall_day, source = get_daily_rainfall_chirps(lat, lon, selected_date)
    if rainfall_3d == 0.0:
        rainfall_3d, _ = get_3day_rainfall_chirps(lat, lon, selected_date)


col1, col2 = st.columns(2)
col1.metric(f"Rainfall (mm)", f"{rainfall_day:.2f}")
col2.metric("3-Day Rainfall (mm)", f"{rainfall_3d:.2f}")

# === Optional Map (showing location) ===
map_col, predict_col = st.columns([2, 1])  # Wider map, narrower prediction block

with map_col:
    m = folium.Map(location=[lat, lon], zoom_start=12, control_scale=True)
    folium.Marker(
        [lat, lon],
        popup=f"<b>{selected_district}</b><br>Rainfall Today: {rainfall_day:.2f} mm<br>3-Day Rainfall: {rainfall_3d:.2f} mm",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    # --- VISUALIZE WITH 10KM RADIUS ---
    folium.Circle(
        location=[lat, lon],
        radius=10000,  # 10 km
        color="blue",
        fill=True,
        fill_opacity=0.2,
        popup="10 km radius"
    ).add_to(m)

    st_folium(m, width=1000, height=500)

with predict_col:
    st.markdown("### 🎯 Flood Prediction")
    if st.button("Predict Flood Risk"):
        with st.spinner("Predicting flood risk..."):
            result = get_flood_prediction(month, rainfall_day, rainfall_3d)

            result_dict = dict(result)
            classes_raw = result_dict.get("classes", "[]")
            scores_raw = result_dict.get("scores", "[]")

            # Parse JSON strings safely
            try:
                classes = json.loads(classes_raw.replace("'", '"')) if isinstance(classes_raw, str) else classes_raw
                scores = json.loads(scores_raw.replace("'", '"')) if isinstance(scores_raw, str) else scores_raw
            except json.JSONDecodeError:
                st.error("❌ Failed to parse model response.")
                st.write("🔎 Raw classes:", classes_raw)
                st.write("🔎 Raw scores:", scores_raw)
                classes, scores = [], []

            # Display prediction result
            if classes and scores:
                if '1' in classes:
                    flood_index = classes.index('1')
                    flood_prob = float(scores[flood_index])
                    no_flood_prob = 1 - flood_prob

                    flood_percent = round(flood_prob * 100, 2)
                    no_flood_percent = round(no_flood_prob * 100, 2)

                    st.metric("🌊 Flood Probability", f"{flood_percent}%")
                    st.metric("☀️ No Flood Probability", f"{no_flood_percent}%")

                    predicted_class = "Flood" if flood_prob >= no_flood_prob else "No Flood"

                    if predicted_class == "Flood":
                        st.error(f"🚨 **Predicted: {predicted_class}**")
    
                        # Send email alerts to all subscribers
                        subscribers = load_subscribers()
                        if subscribers:
                            st.info(f"📧 Sending flood alerts to {len(subscribers)} subscribers...")
                            for sub_email in subscribers:
                                send_email_smtp(
                                    subject="🌊 Flood Alert!",
                                    message_html=f"""
                                        <h2>🚨 Flood Predicted!</h2>
                                        <p>A potential flood has been predicted for <b>{selected_district}</b> on {selected_date.strftime('%Y-%m-%d')}.</p>
                                        <p>Rainfall Today: {rainfall_day:.2f} mm<br>3-Day Rainfall: {rainfall_3d:.2f} mm</p>
                                        <p>Stay safe and follow local authorities' instructions.</p>
                                    """,
                                    to_email=sub_email
                                )
                        st.success("✅ Flood alerts sent to all subscribers!")
                    else:
                        st.success(f"✅ **Predicted: {predicted_class}**")
                else:
                    st.error("❌ Class '1' (Flood) not found in model response.")
                    st.write("🔎 Classes:", classes)
            else:
                st.error("❌ No predictions returned.")

# === GRAPH FOR VISUALIZATION ===
st.subheader(f"📊 Rainfall Trends for {selected_district}")

# Function to fetch past 14 days of rainfall (you can modify this to use your existing functions)
@st.cache_data(ttl=3600)
def get_past_rainfall(lat, lon, end_date, days=14, suppress_warnings=False):
    dates = [end_date - datetime.timedelta(days=i) for i in range(days-1, -1, -1)]
    rainfall_values = []
    
    for d in dates:
        result = get_openmeteo_rainfall(lat, lon, d, d, suppress_warnings=True)
        if result:
            daily = result["daily_rainfall"]
        else:
            daily, _ = get_daily_rainfall_gee(lat, lon, d, suppress_warnings=True)
            if daily == 0.0:
                daily, _ = get_daily_rainfall_chirps(lat, lon, d, suppress_warnings=True)
        rainfall_values.append(daily)
    
    df = pd.DataFrame({
        "Date": dates,
        "Daily Rainfall (mm)": rainfall_values
    })
    df["3-Day Rainfall (mm)"] = df["Daily Rainfall (mm)"].rolling(window=3).sum()
    return df

# Get past rainfall data
rainfall_df = get_past_rainfall(lat, lon, selected_date, suppress_warnings=False)

# Create the plot
fig = go.Figure()

# Daily rainfall bar
fig.add_trace(go.Bar(
    x=rainfall_df["Date"],
    y=rainfall_df["Daily Rainfall (mm)"],
    name="Daily Rainfall",
    marker_color="skyblue"
))

# 3-Day cumulative rainfall line
fig.add_trace(go.Scatter(
    x=rainfall_df["Date"],
    y=rainfall_df["3-Day Rainfall (mm)"],
    mode="lines+markers",
    name="3-Day Cumulative Rainfall",
    line=dict(color="orange", width=2)
))

# Layout settings
fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Rainfall (mm)",
    legend_title="Legend",
    template="plotly_white",
    hovermode="x unified"
)

# Show the plot
st.plotly_chart(fig, use_container_width=True)
# === NOTIFICATION SUBSCRIPTION ===

st.header("🌊 Flood Alert Subscription")

email = st.text_input("📩 Subscribe with your email to receive flood alerts:")

col1, col2 = st.columns(2)
with col1:
    if st.button("Subscribe"):
        if email:
            if add_subscriber(email):
                st.success(f"✅ {email} subscribed successfully!")
            else:
                st.info(f"ℹ️ {email} is already subscribed.")
        else:
            st.error("⚠️ Please enter a valid email.")

with col2:
    if st.button("Unsubscribe"):
        if email:
            if remove_subscriber(email):
                st.success(f"❌ {email} unsubscribed successfully.")
            else:
                st.info("ℹ️ {email} is not in the subscriber list.")
        else:
            st.error("⚠️ Please enter your email.")
