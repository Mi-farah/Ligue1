import requests
import json
import pandas as pd
from datetime import datetime
import sys

API_KEY = sys.argv[1]

data_df=pd.read_csv("localisation_stade.csv",index_col=0)


l_type=[]
l_nom=[]
l_trajet=[]
l_steps=[]
l_distance=[]
l_time=[]
l_vehicule_type=[]

for i in data_df.index:
    print(i)
    origin=data_df.iloc[i,0]
    origin_lat=str(data_df.iloc[i,3])
    origin_lon=str(data_df.iloc[i,4])
    origin_coordinate=origin_lat+','+origin_lon
    for j in data_df.index:
        if i !=j:
            destination=data_df.iloc[j,0]
            destination_lat=str(data_df.iloc[j,3])
            destination_lon=str(data_df.iloc[j,4])
            destination_coordinate=destination_lat+','+destination_lon
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": origin_coordinate,  
                "destination": destination_coordinate,  
                "mode": "transit",
                "alternatives": "true",
                "key": API_KEY
                }
            response = requests.get(url, params=params)
            data = response.json()
            for k, route in enumerate(data["routes"]):
                l_trajet+=[origin+";-"+destination]
                l_nom+=[origin+"-"+destination+" route "+str(k+1)]
                leg = route["legs"][0]
                mini_step=[]
                mini_distance=[]
                mini_type=[]
                mini_vehicule_type=[]
                mini_time=[]
                for step in leg["steps"]:
                    travel_mode = step["travel_mode"]
                    if travel_mode == "TRANSIT":
                        transit = step["transit_details"]
                        vehicle_type = transit["line"]["vehicle"]["type"]
                        if vehicle_type in ["LONG_DISTANCE_TRAIN", "HIGH_SPEED_TRAIN", "HEAVY_RAIL"]:
                            line = transit["line"].get("short_name") or transit["line"].get("name")

                            dep_time = transit["departure_time"]["value"]
                            arr_time = transit["arrival_time"]["value"]
                            mini_time+=[arr_time-dep_time]
                            mini_vehicule_type+=[vehicle_type]
                            mini_type+=[line]
                            dep = transit["departure_stop"]["name"]
                            arr = transit["arrival_stop"]["name"]
                            mini_step+=[dep+";-"+arr]
                            distance = step["distance"]["text"]
                            mini_distance+=[distance] #in km


                l_steps+=[mini_step]
                l_type+=[mini_type]
                l_vehicule_type+=[mini_vehicule_type]
                l_distance+=[mini_distance]
                l_time+=[mini_time]

df_final=pd.DataFrame([])

df_final["Nom"]=l_nom
df_final["trajet"]=l_trajet
df_final["steps"]=l_steps
df_final["type"]=l_type
df_final["distance"]=l_distance
df_final["time"]=l_time
df_final["vehicule_type"]=l_vehicule_type

df_final.to_csv("trajet_train.csv")