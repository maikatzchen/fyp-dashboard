import streamlit as st
import requests

st.title("🌤️ Tomorrow.io Forecast Test")

url = "https://api.tomorrow.io/v4/weather/forecast"
headers = {
    "Authorization": "Bearer plmRZoGH98gI1yHUVxzVzgPnvYTSauk7"
}
params = {
    "location": "42.3478,-71.0466"
}

response = requests.get(url, headers=headers, params=params)

# Display response status
st.write("Status Code:", response.status_code)

# Display JSON response
try:
    data = response.json()
    st.json(data)
except Exception as e:
    st.error(f"Error parsing JSON: {e}")
