import requests

url = "https://api.tomorrow.io/v4/weather/forecast"
headers = {
    "Authorization": "Bearer plmRZoGH98gI1yHUVxzVzgPnvYTSauk7"
}
params = {
    "location": "42.3478,-71.0466"
}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
