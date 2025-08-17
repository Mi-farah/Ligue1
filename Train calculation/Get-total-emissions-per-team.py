import pandas as pd

df=pd.DataFrame([])
data_per_match=pd.read_csv("emission_carbone_match.csv",index_col=0)

list_team=data_per_match["visiting team"].unique()

dict_team = {team: 0 for team in list_team}

for i in data_per_match.index:
    team=data_per_match.iloc[i,1]
    dict_team[team]+=data_per_match.iloc[i,4]


df_final = pd.DataFrame({
    "Equipe": list(dict_team.keys()),
    "Emissions carbone (in kg)": list(dict_team.values())
})

df_final.to_csv("emission_carbone_team.csv")