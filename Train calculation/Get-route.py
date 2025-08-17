import requests
import json
from datetime import datetime

API_KEY = 'AIzaSyDIf4jaKso1v7WmOVfUyZCLBVYmcOJnuH4'
url = 'https://routes.googleapis.com/directions/v2:computeRoutes'


headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": (
        "routes.legs.steps,"
        "routes.distanceMeters,"
        "routes.legs.steps.distanceMeters,"
        "routes.legs.steps.transitDetails,"
        "routes.legs.steps.navigationInstruction"
    )
}

body = {
    "origin": {
        "location": {
            "latLng": {"latitude": 48.844982, "longitude": 2.373577}  # Paris
        }
    },
    "destination": {
        "location": {
            "latLng": {"latitude": 43.589928, "longitude":  1.423031}  # Lyon
        }
    },
    "travelMode": "TRANSIT"
}


response = requests.post(url, headers=headers, data=json.dumps(body))
data = response.json()

for i, route in enumerate(data["routes"]):
    print(f"\n🧭 Route Option {i+1}")
    total_duration_seconds = 0
    for step in data["routes"][0]["legs"][0]["steps"]:
        distance = step.get("distanceMeters", 0)
        instruction = step.get("navigationInstruction", {}).get("instructions", "[No instruction]")
        transit = step.get("transitDetails")
        
        if transit:
            line = transit["transitLine"]["name"]
            dep = transit["stopDetails"]["departureStop"]["name"]
            arr = transit["stopDetails"]["arrivalStop"]["name"]
            
            dep_time_str = transit["stopDetails"]["departureTime"]
            arr_time_str = transit["stopDetails"]["arrivalTime"]

            dep_time = datetime.fromisoformat(dep_time_str.replace("Z", "+00:00"))
            arr_time = datetime.fromisoformat(arr_time_str.replace("Z", "+00:00"))

            duration = arr_time - dep_time
            total_duration_seconds += duration.total_seconds()

            print(f"🚌 Take {line} from {dep} to {arr} — Duration: {duration} — Distance: {distance/1000:.2f} km")
        else:
            print(f"🚶 {instruction}")