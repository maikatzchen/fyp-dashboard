import streamlit as st
import pandas as pd
import requests
import datetime

# NASA GES DISC API endpoint for IMERG Final Run
IMERG_API_URL = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.06"

def get_imerg_precipitation(lat, lon, start_date, end_date):
    """
    Get daily accumulated IMERG rainfall (mm) for given lat/lon and date range
    """
    try:
        # NASA GES DISC requires Earthdata Login for API access
        username = st.secrets["nasa_username"]
        password = st.secrets["nasa_password"]
        
        session = requests.Session()
        session.auth = (username, password)

        # Construct date range
        dates = pd.date_range(start_date, end_date)
        precipitation_data = []

        for date in dates:
            date_str = date.strftime('%Y%m%d')
            # Example dataset URL for one day (adjust for actual endpoint)
            file_url = f"{IMERG_API_URL}/{date.year}/{date.month:02d}/3B-DAY.MS.MRG.3IMERG.{date_str}-S000000-E235959.V06.nc4"

            # Here you would normally fetch and process NetCDF file
            # But for REST API: directly query gridded value (lat/lon)
            # This part requires NASA Earthdata login and OpenDAP or NetCDF4
            
            # For now, simulate a dummy value (replace with actual data fetch)
            rainfall_mm = 10.0  # Dummy placeholder
            precipitation_data.append({'Date': date, 'Precipitation (mm)': rainfall_mm})

        # Convert to DataFrame
        df = pd.DataFrame(precipitation_data)
        return df

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


# Streamlit UI
st.title("🌧️ NASA IMERG Rainfall Data Dashboard")

lat = st.number_input("Enter Latitude", value=5.4204)  # Terengganu example
lon = st.number_input("Enter Longitude", value=103.1025)
start_date = st.date_input("Start Date", datetime.date(2022, 12, 1))
end_date = st.date_input("End Date", datetime.date(2022, 12, 7))

if st.button("Get Rainfall Data"):
    with st.spinner('Fetching IMERG data...'):
        df = get_imerg_precipitation(lat, lon, start_date, end_date)
        if df.empty:
            st.warning("No data returned for the selected range.")
        else:
            st.success("Data loaded successfully!")
            st.dataframe(df)
            st.line_chart(df.set_index('Date'))
