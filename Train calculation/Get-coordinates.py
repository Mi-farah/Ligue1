import requests
import pandas as pd
import sys

data_df= pd.read_csv("name-stade.csv")
API_KEY = sys.argv[1]

lat_list=[]
lon_list=[]

for i in data_df["Stadium"]:
    place_name = i
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&key={API_KEY}"

    response = requests.get(url)
    data = response.json()



    if data['status'] == 'OK':
        location = data['results'][0]['geometry']['location']
        lat = location['lat']
        lng = location['lng']
        lat_list+=[lat]
        lon_list+=[lng]
        print(f"Coordinates of {place_name}: {lat}, {lng}")
    else:
        print("Place not found or error:", data['status'])
    
data_df["latitude"]=lat_list
data_df["longitude"]=lon_list
print(data_df)
data_df.to_csv("localisation_stade.csv")