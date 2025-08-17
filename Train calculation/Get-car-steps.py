import pandas as pd
import requests
import ast
import sys

API_KEY = sys.argv[1]
df_train=pd.read_csv("trajet_train.csv",index_col=0)
df_teams=pd.read_csv("localisation_stade.csv",index_col=0)
df_gare_loc=pd.read_csv("coordinates_gare.csv",index_col=0)
df_train["steps"] = df_train["steps"].apply(ast.literal_eval)

def get_station(trajet):
    part1, part2 = trajet.rsplit(';-', 1)
    return part1,part2

def get_coordinates_stadium(team):
    row=df_teams[df_teams["Team"]==team]
    lat=row["latitude"].values[0]
    lon=row["longitude"].values[0]
    return(lat,lon)


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

l_distance=[]
l_time=[]
for i in df_train.index:
    print(i)
    departure,arrival=get_station(df_train.iloc[i,1])
    dep_lat,dep_lon=get_coordinates_stadium(departure)
    arr_lat,arr_lon=get_coordinates_stadium(arrival)
    l=df_train.iloc[i,2]
    distance=0
    time=0
    if len(l)>0:
        for j in range(len(l)):
            if j==0:
                cor1=str(dep_lat)+","+str(dep_lon)
                gare1,gare2=get_station(l[j])
                cor2=df_gare_loc[df_gare_loc["Gare"]=="Gare "+gare1]["coordinates"]
                d,t=get_distance_duration(cor1,cor2)
                distance+=d
                time += t
            else:
                if len(l)>1:
                    gare1,gare2=get_station(l[j-1])
                    gare3,gare4=get_station(l[j])
                    if gare2 != gare3:
                        cor1=df_gare_loc[df_gare_loc["Gare"]=="Gare "+gare2]["coordinates"]
                        cor2=df_gare_loc[df_gare_loc["Gare"]=="Gare "+gare3]["coordinates"]
                        d,t=get_distance_duration(cor1,cor2)
                        distance+=d
                        time += t
        gare1,gare2=get_station(l[len(l)-1])
        cor1=df_gare_loc[df_gare_loc["Gare"]=="Gare "+gare2]["coordinates"]
        cor2=str(arr_lat)+","+str(arr_lon)
        d,t=get_distance_duration(cor1,cor2)
        distance+=d
        time += t
    else:
        cor1=str(dep_lat)+","+str(dep_lon)
        cor2=str(arr_lat)+","+str(arr_lon)
        d,t=get_distance_duration(cor1,cor2)
        distance+=d
        time += t
    l_distance+=[distance]
    l_time+=[time]

df_train["distance_autocar"]=l_distance
df_train["duration_autocar"]=l_time

df_train.to_csv("trajet_complet.csv")