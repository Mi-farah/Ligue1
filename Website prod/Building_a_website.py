from flask import Flask, render_template,request
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
import shutil

df_plane_trajet = pd.read_csv('../Plane calculation/emission_carbone_match.csv',index_col=0)
df_train_trajet= pd.read_csv('../Train calculation/emission_carbone_match.csv',index_col=0)
df_cars_trajet= pd.read_csv('../Train calculation/trajet_voiture.csv',index_col=0)



def get_emmission_train(hosting_team,visiting_team):
    result = df_train_trajet[
        (df_train_trajet["Hosting team"] == hosting_team) &
        (df_train_trajet["visiting team"] == visiting_team)
    ]
    return(result.iloc[0,2],result.iloc[0,3],result.iloc[0,4])

def get_emission_voiture(hosting_team,visiting_team):
    trajet=hosting_team+";-"+visiting_team
    mini_df=df_cars_trajet[df_cars_trajet["trajet"]==trajet]
    return(mini_df["time"].iloc[0],mini_df["emission"].iloc[0]/1000000)

def get_emission_by_policy(time):
    df_plane_trajet_copy=df_plane_trajet.copy()
    hour=int(time)
    minute=(time-hour)*60
    seconds=minute*60+hour*3600
    for i in df_plane_trajet.index:
        hosting_team=df_plane_trajet.iloc[i,0]
        visiting_team=df_plane_trajet.iloc[i,1]
        time_train,nb_steps,emission=get_emmission_train(hosting_team,visiting_team)
        time_car,emission_car=get_emission_voiture(hosting_team,visiting_team)
        if time_train<seconds or time_car<seconds:
                if nb_steps<3 and time_train<seconds:
                    df_plane_trajet_copy.iloc[i,3]=emission
                else:
                    df_plane_trajet_copy.iloc[i,3]=emission_car
    return(df_plane_trajet_copy)

def get_final_df(df_p):
    list_team=df_p["visiting team"].unique()
    dict_team = {team: 0 for team in list_team}
    for i in df_p.index:
        team=df_p.iloc[i,1]
        dict_team[team]+=df_p.iloc[i,3]
    df_final = pd.DataFrame({
        "Equipe": list(dict_team.keys()),
        "Emissions carbone (kgCO2)": list(dict_team.values())
    })
    return(df_final)



app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    df = pd.read_csv("emission_team.csv")

    # Initial graphs
    total_plane = df["Emission plane (kgCO2)"].sum()
    total_train = df["Emission train (kgCO2)"].sum()

    fig_total = go.Figure([
        go.Bar(name="Plane", x=["Plane"], y=[total_plane], marker_color="crimson"),
        go.Bar(name="Train", x=["Train"], y=[total_train], marker_color="green")
    ])
    fig_total.update_layout(
        title="Total Carbon Emissions (All Teams)",
        yaxis_title="CO₂ Emissions (kg)",
        template="plotly_white"
    )
    graph_total_html = pio.to_html(fig_total, full_html=False)

    trace_real = go.Bar(
        x=df['Equipe'],
        y=df["Emission plane (kgCO2)"],
        name='Actual Emissions',
        marker_color='crimson'
    )
    trace_train = go.Bar(
        x=df['Equipe'],
        y=df["Emission train (kgCO2)"],
        name='If Teams Used Trains',
        marker_color='green'
    )

    fig_teams = go.Figure(data=[trace_real, trace_train])
    fig_teams.update_layout(
        barmode='group',
        title='Team Carbon Emissions: Real vs Train Travel',
        xaxis_title='Team',
        yaxis_title='CO₂ Emissions (kg)',
        template='plotly_white'
    )
    graph_teams_html = pio.to_html(fig_teams, full_html=False)

    # Default values for bar graphs
    graph_total_bar_html = None
    graph_teams_bar_html = None
    result = None
    time = 0

    if request.method == "POST":
        time = float(request.form.get("distance"))
        result=f"New emissions calculated using {time}h time threshold."

        # Compute modified emissions
        df_modified = get_emission_by_policy(time)
        df_bar = get_final_df(df_modified)

        # Sum total emissions after policy
        total_policy_emissions = df_bar["Emissions carbone (kgCO2)"].sum()

        # Create bar chart showing total emissions only
        fig_total_bar = go.Figure([
            go.Bar(name="Plane", x=["Actual emissions"], y=[total_plane], marker_color="crimson"),
            go.Bar(name="Policy Emissions", x=["Emissions after policy change"], y=[total_policy_emissions], marker_color="orange")
        ])
        fig_total_bar.update_layout(
            title=f"Total Emissions After Time Policy (Time < {time}h)",
            yaxis_title="CO₂ Emissions (kg)",
            template="plotly_white"
        )
        graph_total_bar_html = pio.to_html(fig_total_bar, full_html=False)


        

        # Merge both on team name ("Equipe")
        df_compare = pd.merge(df, df_bar, on="Equipe")

        # Create grouped bar chart comparing real vs policy emissions
        fig_compare = go.Figure([
            go.Bar(
                name="Actual Emissions",
                x=df_compare["Equipe"],
                y=df_compare["Emission plane (kgCO2)"],
                marker_color='crimson'
            ),
            go.Bar(
                name=f"Modified Emissions (cutoff = {time}h)",
                x=df_compare["Equipe"],
                y=df_compare["Emissions carbone (kgCO2)"],
                marker_color='orange'
            )
        ])

        fig_compare.update_layout(
            barmode='group',
            title="Team Emissions: Actual vs After Time-Based Train Policy",
            xaxis_title="Team",
            yaxis_title="CO₂ Emissions (kg)",
            template="plotly_white"
        )

        graph_teams_bar_html = pio.to_html(fig_compare, full_html=False)

    return render_template("index.html",
                           graph_total_html=graph_total_html,
                           graph_teams_html=graph_teams_html,
                           graph_total_bar_html=graph_total_bar_html,
                           graph_teams_bar_html=graph_teams_bar_html,
                           time_result=result)

if __name__ == '__main__':
    app.run(debug=True)
