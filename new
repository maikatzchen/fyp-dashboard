import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
import ee
import geemap

# 🛰️ Initialize Earth Engine
ee.Initialize()

# 📡 Public Infobanjir API URLs
rainfall_url = "https://publicinfobanjir.water.gov.my/api/hujan/stesen"
reading_url = "https://publicinfobanjir.water.gov.my/api/hujan/bacaan"

# 🚀 Fetch Infobanjir station metadata
@st.cache_data(ttl=300)
def fetch_stations():
    res = requests.get(rainfall_url)
    return pd.DataFrame(res.json()['data'])

# 🚀 Fetch Infobanjir latest rainfall readings
@st.cache_data(ttl=300)
def fetch_readings():
    res = requests.get(reading_url)
    return pd.DataFrame(res.json()['data'])

# 🗺️ Plot Infobanjir stations on map
def plot_infobanjir_map(stations_df, readings_df):
    m = folium.Map(location=[4.5, 102.0], zoom_start=6, tiles="CartoDB positron")
    for _, row in readings_df.iterrows():
        station = stations_df[stations_df['id'] == row['id']]
        if not station.empty:
            lat, lon = station.iloc[0]['latitude'], station.iloc[0]['longitude']
            name = station.iloc[0]['nama']
            value = row['bacaan']
            time = row['tarikh']
            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                popup=f"<b>{name}</b><br>Rainfall: {value}mm<br>{time}",
                color="blue" if value < 20 else "orange" if value < 50 else "red",
                fill=True,
                fill_opacity=0.7
            ).add_to(m)
    return m

# 🛰️ Plot IMERG satellite rainfall map
def plot_imerg_map():
    Map = geemap.Map(center=[4.5, 102.0], zoom=6)
    dataset = ee.ImageCollection('NASA/GPM_L3/IMERG_V06')
    recent = dataset.sort('system:time_start', False).first()
    rainfall = recent.select('precipitationCal')
    vis_params = {
        'min': 0.0,
        'max': 50.0,
        'palette': ['blue', 'cyan', 'lime', 'yellow', 'red']
    }
    Map.addLayer(rainfall, vis_params, 'IMERG Rainfall (mm/hr)')
    return Map

# 🎯 Streamlit App UI
st.set_page_config(page_title="FYP Rainfall Dashboard", layout="wide")
st.title("🌧️ FYP Hybrid Rainfall Dashboard")

# 🔀 Tabs for switching between data sources
tab1, tab2 = st.tabs(["📍 Ground Stations (Infobanjir)", "🛰️ Satellite View (NASA IMERG)"])

with tab1:
    st.subheader("📍 Malaysia Real-Time Rainfall (Ground Stations)")
    stations_df = fetch_stations()
    readings_df = fetch_readings()
    st.info(f"Fetched {len(readings_df)} live rainfall readings from {len(stations_df)} stations.")
    infobanjir_map = plot_infobanjir_map(stations_df, readings_df)
    st_folium(infobanjir_map, width=800, height=600)

with tab2:
    st.subheader("🛰️ Satellite Rainfall (NASA IMERG - Near Real-Time)")
    imerg_map = plot_imerg_map()
    imerg_map.to_streamlit(width=800, height=600)
