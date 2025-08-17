import pandas as pd
import ast
import re
import sys

df=pd.DataFrame([])

team_df=pd.read_csv("name-stade.csv")
trajet_df=pd.read_csv("trajet_complet.csv",index_col=0)
car_trips_df=pd.read_csv("trajet_voiture.csv",index_col=0)

list_team=list(team_df["Team"])

#Source: https://bigmedia.bpifrance.fr/nos-dossiers/empreinte-carbone-des-trajets-en-train-calcul-et-decarbonation
Emission_TGV=3.5 #gCO2/passagers/km
Emission_train=7.5 #gCO2/passagers/km
Emission_autocar=30 #gCO2/passagers/km
Nombre_passagers=50#sys.argv[1]

list1=[]
list2=[]
for i in list_team:
    for j in list_team:
        if i!=j:
            list1+=[i]
            list2+=[j]


df["Hosting team"]=list1
df["visiting team"]=list2

trajet_df["time"] = trajet_df["time"].apply(ast.literal_eval)
trajet_df["distance"] = trajet_df["distance"].apply(ast.literal_eval)
trajet_df["type"] = trajet_df["type"].apply(ast.literal_eval)
trajet_df["vehicule_type"] = trajet_df["vehicule_type"].apply(ast.literal_eval)
trajet_df["steps"] = trajet_df["steps"].apply(ast.literal_eval)

type=[]
for i in trajet_df.index:
    for j in trajet_df.iloc[i,6]:
        if j not in type:
            type+=[j]



total_time_list=[]
number_steps_list=[]
for i in trajet_df.index:
    time=0
    for j in list(trajet_df.iloc[i,5]):
        time+=int(j)
    time+=trajet_df.iloc[i,8]
    n=len(trajet_df.iloc[i,2])
    total_time_list+=[time]
    number_steps_list+=[n]

trajet_df["total_time"]=total_time_list
trajet_df["number of steps"]=number_steps_list




def get_fastest_route(hosting_team, visiting_team): 
    mini_df = trajet_df[trajet_df["trajet"] == visiting_team + ";-" + hosting_team]
    print(visiting_team + ";-" + hosting_team)
    direct_routes = mini_df[mini_df["number of steps"]==2]

    if not direct_routes.empty:
        best_route = direct_routes[direct_routes["total_time"] == direct_routes["total_time"].min()]
    else:
        best_route = mini_df[mini_df["total_time"] == mini_df["total_time"].min()]

    return best_route.iloc[0]



def get_emission_carbone(mini_df):
    emission=0
    for i in range(len(mini_df["distance"])):
        dist=re.search(r"\d+",mini_df["distance"][i]).group()
        if mini_df["vehicule_type"][i]=="HIGH_SPEED_TRAIN":
            emission+=int(dist)*Emission_TGV
        else:
            emission+=int(dist)*Emission_train
    emission+=mini_df["distance_autocar"]*Emission_autocar/1000
    return(emission/1000) #kgCO2/passager


def is_direct_time(df):
    return(df.loc["number of steps"],df.loc["total_time"])


def car_trip_alternative(hosting_team,visiting_team):
     mini_df = car_trips_df[car_trips_df["trajet"] == visiting_team + ";-" + hosting_team]
     return(mini_df["emission"].iloc[0]/1000000,mini_df["time"].iloc[0]) ##kgCO2/passager,seconds



print(df)
emission_list=[]
steps_list=[]
time_list=[]
for i in range(len(df.index)):
    emission=0
    hosting_team=df.iloc[i,0]
    visiting_team=df.iloc[i,1]
    mini_df=get_fastest_route(hosting_team,visiting_team)
    steps,time=is_direct_time(mini_df)
    car_emission,car_time=car_trip_alternative(hosting_team,visiting_team)
    if car_time<time:
        emission=car_emission*Nombre_passagers #Déjà un aller_retour pris en consideration
        emission_list+=[emission]
        steps_list+=[1]
        time_list+=[car_time]
    else:
        emission=get_emission_carbone(mini_df)*2*Nombre_passagers #Aller_retour
        emission_list+=[emission]
        steps_list+=[steps]
        time_list+=[time]




df["Time"]=time_list
df["Number of steps"]=steps_list
df["emission_carbone"]=emission_list
print(df)

df.to_csv("emission_carbone_match.csv")