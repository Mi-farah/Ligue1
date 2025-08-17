import pandas as pd

df_plane=pd.read_csv("../Plane calculation/emission_carbone_team.csv",index_col=0)
df_train=pd.read_csv("../train calculation/emission_carbone_team.csv",index_col=0)

df = pd.merge(
    df_plane,
    df_train,
    on=df_plane.columns[0],
    how='inner',
    suffixes=('_plane', '_train')
)

# Rename columns for clarity
df.columns = ['Equipe', 'Emission plane (kgCO2)', 'Emission train (kgCO2)']

# Optional: reset index if needed
df.reset_index(drop=True, inplace=True)

print(df)

df.to_csv("emission_team.csv")