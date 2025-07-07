import streamlit as st
import requests

st.title("🌤️ Tomorrow.io v3 Realtime Weather")

url = "https://api.tomorrow.io/v3/weather/realtime"
params = {
    "location": "42.3478,-71.0466",
    "apikey": "plmRZoGH98gI1yHUVxzVzgPnvYTSauk7"
}

response = requests.get(url, params=params)
st.write("Status Code:", response.status_code)

try:
    data = response.json()
    st.json(data)
except Exception as e:
    st.error(f"Error parsing JSON: {e}")
