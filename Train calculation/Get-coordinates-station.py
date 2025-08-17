import pandas as pd
import requests
import ast
import sys

API_KEY = sys.argv[1]



def get_station(trajet):
    part1, part2 = trajet.rsplit(';-', 1)
    return part1,part2

def get_coordinates(station):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={station}&key={API_KEY}"

    response = requests.get(url)
    data = response.json()

    if data['status'] == 'OK':
        location = data['results'][0]['geometry']['location']
        lat = location['lat']
        lng = location['lng']
    else:
        station=station.replace("Gare ", "")
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={station}&key={API_KEY}"
        response = requests.get(url)
        data = response.json()

        location = data['results'][0]['geometry']['location']
        lat = location['lat']
        lng = location['lng']
        
    return lat,lng

data_df=pd.read_csv("trajet_train.csv",index_col=0)
data_df["steps"] = data_df["steps"].apply(ast.literal_eval)

stations=[]
for i in range(len(data_df.index)):
    l=data_df.iloc[i,2]
    for j in l:
        part1,part2=get_station(str(j))
        if part1 not in stations:
            stations+=["Gare "+part1]
        if part2 not in stations:
            stations+=["Gare "+part2]


dict_station = {station: "" for station in stations}
print(dict_station)

for k in dict_station.keys():
    print(k)
    lat,lon=get_coordinates(k)
    dict_station[k]=f"{lat},{lon}"

df_final = pd.DataFrame({
    "Gare": list(dict_station.keys()),
    "coordinates": list(dict_station.values())
})

df_final.to_csv("coordinates_gare.csv")
