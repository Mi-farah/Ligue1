import requests
import json
from datetime import datetime

API_KEY = 'AIzaSyDIf4jaKso1v7WmOVfUyZCLBVYmcOJnuH4'


url = "https://maps.googleapis.com/maps/api/directions/json"
params = {
    "origin": "47.476298, -0.562938",  # Paris
    "destination": "50.627678, 3.060877",  # Lyon
    "mode": "transit",
    "alternatives": "true",
    "key": API_KEY
}

response = requests.get(url, params=params)
data = response.json()

print(data)

for i, route in enumerate(data["routes"]):
    print(f"\n🧭 Route Option {i + 1}")
    leg = route["legs"][0]
    print(f"Total Duration: {leg['duration']['text']} | Distance: {leg['distance']['text']}")

    for step in leg["steps"]:
        travel_mode = step["travel_mode"]
        instruction = step.get("html_instructions", "[No instruction]")
        distance = step["distance"]["text"]

        if travel_mode == "TRANSIT":
            transit = step["transit_details"]
            line = transit["line"]["short_name"] if "short_name" in transit["line"] else transit["line"]["name"]
            dep = transit["departure_stop"]["name"]
            arr = transit["arrival_stop"]["name"]
            dep_time = transit["departure_time"]["text"]
            arr_time = transit["arrival_time"]["text"]

            print(f"🚌 Take {line} from {dep} at {dep_time} to {arr} at {arr_time} — Distance: {distance}")
        else:
            print(f"🚶 {instruction} — Distance: {distance}")