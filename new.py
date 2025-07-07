import streamlit as st
import requests

st.title("🌤️ Tomorrow.io Realtime Weather (v3 API)")

url = "https://api.tomorrow.io/v3/weather/realtime"
params = {
    "location": "42.3478,-71.0466",
    "apikey": "plmRZoGH98gI1yHUVxzVzgPnvYTSauk7"
}

response = requests.get(url, params=params)

# Display response status
st.write("Status Code:", response.status_code)

# Display JSON response
try:
    data = response.json()
    st.json(data)
except Exception as e:
    st.error(f"Error parsing JSON: {e}")
