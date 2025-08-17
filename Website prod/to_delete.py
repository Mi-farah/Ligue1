import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
import shutil

df_plane_trajet = pd.read_csv('../Plane calculation/emission_carbone_match.csv',index_col=0)
df_train_trajet= pd.read_csv('../Train calculation/emission_carbone_match.csv',index_col=0)



def get_emmission_train(hosting_team,visiting_team):
    result = df_train_trajet[
        (df_train_trajet["Hosting team"] == hosting_team) &
        (df_train_trajet["visiting team"] == visiting_team)
    ]
    return(result.iloc[0,2])



def get_emission_by_policy(time):
    df_plane_trajet_copy=df_plane_trajet.copy()
    hour=int(time)
    minute=(time-hour)*60
    seconds=minute*60+hour*3600
    for i in df_plane_trajet.index:
        if df_plane_trajet.iloc[i,2]<seconds:
            hosting_team=df_plane_trajet.iloc[i,0]
            visiting_team=df_plane_trajet.iloc[i,1]
            df_plane_trajet_copy.iloc[i,3]=get_emmission_train(hosting_team,visiting_team)
    return(df_plane_trajet_copy)


def get_final_df(df_p):
    list_team=df_p["visiting team"].unique()
    print(df_p.columns)
    dict_team = {team: 0 for team in list_team}
    for i in df_p.index:
        team=df_p.iloc[i,1]
        dict_team[team]+=df_p.iloc[i,3]
    df_final = pd.DataFrame({
        "Equipe": list(dict_team.keys()),
        "Emissions carbone (kgCO2)": list(dict_team.values())
    })
    return(df_final)


print(get_final_df(get_emission_by_policy(1.5)))