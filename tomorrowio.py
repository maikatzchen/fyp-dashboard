import streamlit as st
import pandas as pd
import requests
import datetime

TOMORROW_API_KEY = "YOUR_API_KEY_HERE"

def get_tomorrow_rainfall_area(lat, lon, start_date, end_date, radius_km=3):
    """
    Get daily rainfall (mm) from Tomorrow.io API within a radius (in km)
    around given lat/lon
    """
    # Approx. degrees for radius (1° ~ 111km)
    delta_deg = radius_km / 111.0

    # Bounding box: [west,south,east,north]
    west = lon - delta_deg
    south = lat - delta_deg
    east = lon + delta_deg
    north = lat + delta_deg

    url = "https://api.tomorrow.io/v4/weather/history/recent"

    params = {
        "apikey": TOMORROW_API_KEY,
        "fields": "precipitationAmount",
        "timesteps": "1d",
        "startTime": start_date.strftime("%Y-%m-%dT00:00:00Z"),
        "endTime": end_date.strftime("%Y-%m-%dT23:59:59Z"),
        "bbox": f"{south},{west},{north},{east}",
        "units": "metric"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        st.error(f"API error: {response.status_code} - {response.text}")
        return pd.DataFrame()

    data = response.json()
    st.write(data)  # Debug: See raw API response

    try:
        # Extract daily data (average for the area)
        intervals = data['data']['timelines'][0]['intervals']

        df = pd.DataFrame([{
            "Date": interval['startTime'][:10],
            "Precipitation (mm)": interval['values']['precipitationAmount']
        } for interval in intervals])

        df['Date'] = pd.to_datetime(df['Date'])
        return df

    except (KeyError, IndexError):
        st.warning("No rainfall data found for this area and date range.")
        return pd.DataFrame()


# Streamlit UI
st.title("🌧️ Rainfall Data (Tomorrow.io with 3km Bound)")

lat = st.number_input("Enter Latitude", value=4.7500)  # Dungun example
lon = st.number_input("Enter Longitude", value=103.4100)
start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=7))
end_date = st.date_input("End Date", datetime.date.today())

if st.button("Get Rainfall Data"):
    with st.spinner('Fetching Tomorrow.io rainfall data for 3 km bound...'):
        df = get_tomorrow_rainfall_area(lat, lon, start_date, end_date)
        if df.empty:
            st.warning("No data returned for the selected area and range.")
        else:
            st.success("Data loaded successfully!")
            st.dataframe(df)
            st.line_chart(df.set_index('Date'))
