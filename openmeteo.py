import streamlit as st
import pandas as pd
import requests
import datetime

CORRECTION_FACTOR = 0.45  # Bias correction factor

def get_openmeteo_rainfall_5x5_grid(lat, lon, start_date, end_date):
    """
    Get average daily rainfall (mm) within 3km bound using 5x5 grid
    """
    st.info(f"Fetching rainfall data within ~3km radius of ({lat}, {lon}) using 5x5 grid")

    # Approximate 3km in degrees (~0.027 degrees)
    offset_deg = 0.0135  # 3km / 2 divided across 2 grid steps
    grid_range = [-2, -1, 0, 1, 2]  # For 5x5 grid

    all_df = []

    point_num = 1
    for dx in grid_range:
        for dy in grid_range:
            lat_offset = lat + (dx * offset_deg)
            lon_offset = lon + (dy * offset_deg)
            st.write(f"📍 Querying Point {point_num}: ({lat_offset:.5f}, {lon_offset:.5f})")
            point_num += 1

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
                st.error(f"API error at Point {point_num-1}: {response.status_code}")
                continue

            data = response.json()
            try:
                dates = data['daily']['time']
                precipitation = data['daily']['precipitation_sum']

                df = pd.DataFrame({
                    "Date": pd.to_datetime(dates),
                    "Precipitation (mm)": precipitation
                })
                all_df.append(df)

            except KeyError:
                st.warning(f"No rainfall data found at Point {point_num-1}")
                continue

    if not all_df:
        st.error("No data fetched for any grid points.")
        return pd.DataFrame()

    # Combine all grid data
    combined_df = pd.concat(all_df).groupby("Date").mean().reset_index()
    combined_df["Corrected (mm)"] = combined_df["Precipitation (mm)"] * CORRECTION_FACTOR

    return combined_df


# 🌧️ Streamlit UI
st.title("🌧️ Real-time Rainfall Data (Open-Meteo API with 5x5 Grid)")

lat = st.number_input("Enter Latitude", value=5.4204, format="%.5f")  # Default: Terengganu
lon = st.number_input("Enter Longitude", value=103.1025, format="%.5f")
start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=7))
end_date = st.date_input("End Date", datetime.date.today())

if st.button("Get Rainfall Data"):
    with st.spinner('Fetching rainfall data for 5x5 grid...'):
        df = get_openmeteo_rainfall_5x5_grid(lat, lon, start_date, end_date)
        if df.empty:
            st.warning("No data returned for the selected range.")
        else:
            st.success("✅ Data loaded successfully!")
            st.dataframe(df)
            st.line_chart(df.set_index('Date')[["Precipitation (mm)", "Corrected (mm)"]])
