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
        dates = dat
