import streamlit as st
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# Streamlit UI
st.title("Open-Meteo Weather Data")
latitude = st.number_input("Enter Latitude", value=3.1412)
longitude = st.number_input("Enter Longitude", value=101.6865)

if st.button("Get Weather Data"):
    # Setup Open-Meteo API client
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # API Request
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["precipitation", "rain"]
    }
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        
        # Hourly data
        hourly = response.Hourly()
        hourly_precipitation = hourly.Variables(0).ValuesAsNumpy()
        hourly_rain = hourly.Variables(1).ValuesAsNumpy()

        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "precipitation": hourly_precipitation,
            "rain": hourly_rain
        }

        hourly_df = pd.DataFrame(hourly_data)

        st.success(f"Weather data for {latitude}, {longitude}")
        st.dataframe(hourly_df)

        # Optional: Line chart
        st.line_chart(hourly_df.set_index("date")[["precipitation", "rain"]])

    except Exception as e:
        st.error(f"Error fetching data: {e}")
