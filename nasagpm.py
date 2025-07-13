import streamlit as st
import pandas as pd
from gpm_api import GPM
import datetime

# Initialize GPM API
gpm = GPM()

def get_imerg_precipitation(lat, lon, start_date, end_date):
    """
    Get daily accumulated IMERG rainfall (mm) for given lat/lon and date range
    """
    # Convert dates to ISO format
    start_date = start_date.isoformat()
    end_date = end_date.isoformat()

    # Query IMERG Final Run Daily (IMERGDF)
    dataset = gpm.dataset('IMERGDF')
    query = (
        dataset.query()
        .latlon(lat, lon)
        .time(start_date, end_date)
        .variables('precipitationCal')
        .execute()
    )

    # Extract time and precipitation values
    times = query['data']['time']
    values = query['data']['precipitationCal']

    # Create DataFrame
    df = pd.DataFrame({
        'Date': pd.to_datetime(times),
        'Precipitation (mm)': values
    })

    return df

# Streamlit UI
st.title("🌧️ NASA IMERG Rainfall Data Dashboard")

lat = st.number_input("Enter Latitude", value=5.4204)  # Terengganu example
lon = st.number_input("Enter Longitude", value=103.1025)
start_date = st.date_input("Start Date", datetime.date(2022, 12, 1))
end_date = st.date_input("End Date", datetime.date(2022, 12, 7))

if st.button("Get Rainfall Data"):
    with st.spinner('Fetching IMERG data...'):
        try:
            df = get_imerg_precipitation(lat, lon, start_date, end_date)
            if df.empty:
                st.warning("No data returned for the selected range.")
            else:
                st.success("Data loaded successfully!")
                st.dataframe(df)
                st.line_chart(df.set_index('Date'))
        except Exception as e:
            st.error(f"Error fetching data: {e}")
