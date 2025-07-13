import streamlit as st
import pandas as pd
import requests
import datetime

CORRECTION_FACTOR = 0.45

def get_openmeteo_rainfall_3km_bound(lat, lon, start_date, end_date):
    """
    Get average daily rainfall (mm) within 3km bound from Open-Meteo API
    """
    st.info(f"Fetching rainfall data within ~3km radius of ({lat}, {lon})")

    # Approximate 3km in degrees
    offset_deg = 0.027  # ~3km
    offsets = [
        (0, 0),  # Center point
        (offset_deg, offset_deg),    # NE
        (offset_deg, -offset_deg),   # NW
        (-offset_deg, offset_deg),   # SE
        (-offset_deg, -offset_deg)   # SW
    ]

    results = []
    for i, (dlat, dlon) in enumerate(offsets, start=1):
        lat_offset = lat + dlat
        lon_offset = lon + dlon
        st.write(f"📍 Querying Point {i}: ({lat_offset:.5f}, {lon_offset:.5f})")

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat_offset,
            "longitude": lon_offset,
            "daily": "precipitation_sum",
            "timezone": "Asia/Kuala_Lumpur",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            st.error(f"API error at Point {i}: {response.status_code}")
            continue

        data = response.json()
        try:
            dates = data['daily']['time']
            precipitation = data['daily']['precipitation_sum']

            # Apply bias correction
            corrected_precipitation = [p * CORRECTION_FACTOR for p in precipitation]

        df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            "Open-Meteo (mm)": precipitation,
            "Corrected (mm)": corrected_precipitation
        })

            return df

    except KeyError:
        st.warning("No rainfall data found for this date range and location.")
        return pd.DataFrame()


# 🌧️ Streamlit UI
st.title("🌧️ Real-time Rainfall Data (Open-Meteo API with 3km Bound)")

lat = st.number_input("Enter Latitude", value=5.4204, format="%.5f")  # Default: Terengganu
lon = st.number_input("Enter Longitude", value=103.1025, format="%.5f")
start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=7))
end_date = st.date_input("End Date", datetime.date.today())

if st.button("Get Rainfall Data"):
    with st.spinner('Fetching rainfall data for 3km bound...'):
        df = get_openmeteo_rainfall_3km_bound(lat, lon, start_date, end_date)
        if df.empty:
            st.warning("No data returned for the selected range.")
        else:
            st.success("✅ Data loaded successfully!")
            st.dataframe(df)
            st.line_chart(df.set_index('Date'))
