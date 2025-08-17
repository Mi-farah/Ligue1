import pandas as pd
import sys
import requests


API_KEY = sys.argv[0]
data_df=pd.read_csv("localisation_stade.csv",index_col=0)
#Source: https://bigmedia.bpifrance.fr/nos-dossiers/empreinte-carbone-des-trajets-en-train-calcul-et-decarbonation
Emission_autocar=30 #gCO2/passagers/km

def get_distance_duration(cor1, cor2):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": cor1,  
        "destination": cor2, 
        "mode": "driving",
        "alternatives": "false",
        "key": API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    try:
        leg = data["routes"][0]["legs"][0]
        distance_meters = leg["distance"]["value"]           # in meters
        duration_seconds = leg["duration"]["value"]          # in seconds
        return distance_meters, duration_seconds
    except (KeyError, IndexError):
        return None, None



l_trajet=[]
l_distance=[]
l_time=[]
l_emission=[]

for i in data_df.index:
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
            distance_meters,duration_seconds=get_distance_duration(origin_coordinate,destination_coordinate)
            l_trajet+=[origin+";-"+destination]
            l_distance+=[distance_meters]
            l_time+=[duration_seconds]
            l_emission+=[2*distance_meters*Emission_autocar]


df_final=pd.DataFrame([])


df_final["trajet"]=l_trajet
df_final["distance"]=l_distance
df_final["time"]=l_time
df_final["emission"]=l_emission

df_final.to_csv("trajet_voiture.csv")
