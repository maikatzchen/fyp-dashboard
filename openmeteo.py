import streamlit as st
import pandas as pd
import requests
import datetime

def get_openmeteo_rainfall(lat, lon, start_date, end_date):
    """
    Get daily accumulated rainfall (mm) from Open-Meteo API
    """
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "timezone": "Asia/Kuala_Lumpur",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        st.error(f"API error: {response.status_code} - {response.text}")
        return pd.DataFrame()

    data = response.json()

    try:
        dates = data['daily']['time']
        precipitation = data['daily']['precipitation_sum']

        df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            "Precipitation (mm)": precipitation
        })

        return df

    except KeyError:
        st.warning("No rainfall data found for this date range and location.")
        return pd.DataFrame()


# Streamlit UI
st.title("🌧️ Real-time Rainfall Data (Open-Meteo API)")

lat = st.number_input("Enter Latitude", value=5.4204)  # Terengganu example
lon = st.number_input("Enter Longitude", value=103.1025)
start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=7))
end_date = st.date_input("End Date", datetime.date.today())

if st.button("Get Rainfall Data"):
    with st.spinner('Fetching real-time rainfall data...'):
        df = get_openmeteo_rainfall(lat, lon, start_date, end_date)
        if df.empty:
            st.warning("No data returned for the selected range.")
        else:
            st.success("Data loaded successfully!")
            st.dataframe(df)
            st.line_chart(df.set_index('Date'))
