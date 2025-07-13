import streamlit as st
import pandas as pd
import requests
import datetime

# Set your Tomorrow.io API key
TOMORROW_API_KEY = st.secrets["tomorrow_api_key"]

def get_tomorrow_rainfall(lat, lon, start_date, end_date):
    """
    Get daily accumulated rainfall (mm) from Tomorrow.io API
    """
    url = "https://api.tomorrow.io/v4/timelines"

    # Convert dates to ISO 8601
    start_iso = start_date.strftime("%Y-%m-%dT00:00:00Z")
    end_iso = end_date.strftime("%Y-%m-%dT23:59:59Z")

    params = {
        "apikey": TOMORROW_API_KEY,
        "location": f"{lat},{lon}",
        "fields": ["precipitationAmount"],
        "units": "metric",
        "timesteps": "1d",
        "startTime": start_iso,
        "endTime": end_iso
    }

    response = requests.get(url, params=params)
    data = response.json()

    try:
        daily_data = data['data']['timelines'][0]['intervals']
        df = pd.DataFrame([{
            "Date": interval['startTime'][:10],
            "Precipitation (mm)": interval['values']['precipitationAmount']
        } for interval in daily_data])
        df['Date'] = pd.to_datetime(df['Date'])
        return df

    except (KeyError, IndexError) as e:
        st.error("No rainfall data found or API quota exceeded.")
        return pd.DataFrame()  # Empty DataFrame


# Streamlit UI
st.title("🌧️ Real-time Rainfall Data (Tomorrow.io API)")

lat = st.number_input("Enter Latitude", value=5.4204)  # Terengganu example
lon = st.number_input("Enter Longitude", value=103.1025)
start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=7))
end_date = st.date_input("End Date", datetime.date.today())

if st.button("Get Rainfall Data"):
    with st.spinner('Fetching real-time rainfall data...'):
        df = get_tomorrow_rainfall(lat, lon, start_date, end_date)
        if df.empty:
            st.warning("No data returned for the selected range.")
        else:
            st.success("Data loaded successfully!")
            st.dataframe(df)
            st.line_chart(df.set_index('Date'))
