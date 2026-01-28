from typing import Tuple

import pandas as pd


from backend.global_variables import DATA_PATH

data = pd.read_excel(
    "backend/data/Historic_travels/Déplacement-mode.xlsx", sheet_name="Feuil1", header=1
)

emission_plane_data = pd.read_csv(DATA_PATH + "flight_emissions.csv")
emission_train_data = pd.read_csv(DATA_PATH + "train_emissions.csv")
emission_car_data = pd.read_csv(DATA_PATH + "car_emissions.csv")


data_historic_travels = data.iloc[0:18]

reconstructed_data = pd.melt(
    data_historic_travels, id_vars=["v"], var_name="Host team", value_name="Transport"
)

reconstructed_data = reconstructed_data.rename(columns={"v": "Visiting team"})


def get_emissions_and_time(
    visiting_team_name: str, hosting_team_name: str, transport_type: str
) -> Tuple[float, float,float]:
    """
    Get the emissions and time for a given transport mode.
    """
    match transport_type:
        case "avion":
            dataset = emission_plane_data
        case "bus":
            dataset = emission_car_data
        case "train":
            dataset = emission_train_data
        case _:
            return 0.0, 0.0, 0.0

    subset = dataset[
        (dataset["departure"] == visiting_team_name)
        & (dataset["arrival"] == hosting_team_name)
    ]

    if subset.empty:
        subset2 = dataset[
            (dataset["departure"] == hosting_team_name)
            & (dataset["arrival"] == visiting_team_name)
        ]
        emission_in_kg = subset2["emissions_kg_co2"].iloc[0]
        time_in_sec = subset2["travel_time_seconds"].iloc[0]
        distance_km = subset2["distance_km"].iloc[0]
    else:
        emission_in_kg = subset["emissions_kg_co2"].iloc[0]
        time_in_sec = subset["travel_time_seconds"].iloc[0]
        distance_km = subset["distance_km"].iloc[0]

    return (
        emission_in_kg,
        time_in_sec,
        distance_km
    )


def main():
    """
    Calculate the emissions and time for each transport mode.
    """
    # Calculate the emissions and time for each transport mode
    list_visiting_team: list[str] = []
    list_hosting_team: list[str] = []
    list_transport: list[str] =[]
    list_id: list[float] = []
    list_aller_retour: list[str] =[]
    list_emissions: list[float] = []
    list_time: list[float] = []
    list_distance: list[float] = []
    i=1
    for _, row in reconstructed_data.iterrows():
        visiting_team = row["Visiting team"]
        hosting_team = row["Host team"]
        transport = row["Transport"]
        list_visiting_team.append(visiting_team)
        list_hosting_team.append(hosting_team)
        list_visiting_team.append(visiting_team)
        list_hosting_team.append(hosting_team)
        if transport=="Aller en bus\nRetour en avion":
            emission_aller, time_aller, distance_aller = get_emissions_and_time(
            visiting_team, hosting_team, "bus"
            )
            emission_retour, time_retour, distance_retour = get_emissions_and_time(
            visiting_team, hosting_team, "avion"
            )
            list_id.append(i)
            list_transport.append("bus")
            list_aller_retour.append("aller")
            list_emissions.append(emission_aller/2)
            list_time.append(time_aller/2)
            list_distance.append(distance_aller/2)
            list_id.append(i)
            list_aller_retour.append("retour")
            list_transport.append("avion")
            list_emissions.append((emission_retour+emission_aller)/2) # Pour prendre en considération le bus à vide
            list_time.append(time_retour/2)
            list_distance.append(distance_retour/2)
            i+=1
        elif transport=="Aller en train\nRetour en bus":
            emission_aller, time_aller, distance_aller = get_emissions_and_time(
            visiting_team, hosting_team, "train"
            )
            emission_retour, time_retour, distance_retour = get_emissions_and_time(
            visiting_team, hosting_team, "bus"
            )
            list_id.append(i)
            list_transport.append("train")
            list_aller_retour.append("aller")
            list_emissions.append((emission_aller+emission_retour)/2)
            list_time.append(time_aller/2)
            list_distance.append(distance_aller/2)
            list_id.append(i)
            list_aller_retour.append("retour")
            list_transport.append("bus")
            list_emissions.append(emission_retour/2)
            list_time.append(time_retour/2)
            list_distance.append(distance_retour/2)
            i+=1
        else:
            emission, time, distance = get_emissions_and_time(
                visiting_team, hosting_team, transport.lower()
            )

            # if the transport is not bus, we add the emissions of the bus for the empty bus trip
            if transport != "bus" and visiting_team != hosting_team:
                emission_bus1, _, _d_ = get_emissions_and_time(
                    visiting_team, hosting_team, "bus".lower()
                )
                emission += emission_bus1

            list_id.append(i)
            list_aller_retour.append("aller")
            list_transport.append(transport)
            list_emissions.append(emission/2)
            list_time.append(time/2)
            list_distance.append(distance/2)
            list_id.append(i)
            list_transport.append(transport)
            list_aller_retour.append("retour")
            list_emissions.append(emission/2)
            list_time.append(time/2)
            list_distance.append(distance/2)
            i+=1

    # Calculate the alternative emissions and time
    #Scenario1: No Plane
    list_alternative_emissions = []
    list_alternative_time = []
    list_alternative_distance = []
    list_alternative_emissions_wo_bus = []

    #Scenario2: No plane if alternative <4 hours
    time_scenario2=4
    list_alternative2_emissions = []
    list_alternative2_time = []
    list_alternative2_distance = []
    list_alternative2_emissions_wo_bus = []

    #Scenario3: No plane if alternative <6 hours
    time_scenario3=6
    list_alternative3_emissions = []
    list_alternative3_time = []
    list_alternative3_distance = []
    list_alternative3_emissions_wo_bus = []

    for k in range(len(list_id)):
        visiting_team=list_visiting_team[k]
        hosting_team=list_hosting_team[k]
        if list_transport[k]=="avion":
            emission_plane, time_plane, distance_plane = get_emissions_and_time(
                visiting_team, hosting_team, "avion"
            )
            emission_train, time_train, distance_train = get_emissions_and_time(
                visiting_team, hosting_team, "train"
            )
            emission_bus, time_bus, distance_bus = get_emissions_and_time(
                visiting_team, hosting_team, "bus"
            )
            if time_bus<time_train:
                list_alternative_emissions.append(emission_bus/2)
                list_alternative_emissions_wo_bus.append(emission_bus/2)
                list_alternative_time.append(time_bus/2)
                list_alternative_distance.append(distance_bus/2)
                if time_bus < 2*3600*time_scenario2:
                    list_alternative2_emissions.append(emission_bus/2)
                    list_alternative2_emissions_wo_bus.append(emission_bus/2)
                    list_alternative2_time.append(time_bus/2)
                    list_alternative2_distance.append(distance_bus/2)

                    list_alternative3_emissions.append(emission_bus/2)
                    list_alternative3_emissions_wo_bus.append(emission_bus/2)
                    list_alternative3_time.append(time_bus/2)
                    list_alternative3_distance.append(distance_bus/2)
                
                elif time_bus < 2*3600*time_scenario3:
                    list_alternative2_emissions.append((emission_plane+emission_bus)/2)
                    list_alternative2_emissions_wo_bus.append(emission_plane/2)
                    list_alternative2_time.append(time_plane/2)
                    list_alternative2_distance.append(distance_plane/2)

                    list_alternative3_emissions.append(emission_bus/2)
                    list_alternative3_emissions_wo_bus.append(emission_bus/2)
                    list_alternative3_time.append(time_bus/2)
                    list_alternative3_distance.append(distance_bus/2)
                else:
                    list_alternative2_emissions.append((emission_plane+emission_bus)/2)
                    list_alternative2_emissions_wo_bus.append(emission_plane/2)
                    list_alternative2_time.append(time_plane/2)
                    list_alternative2_distance.append(distance_plane/2)

                    list_alternative3_emissions.append((emission_plane+emission_bus)/2)
                    list_alternative3_emissions_wo_bus.append(emission_plane/2)
                    list_alternative3_time.append(time_plane/2)
                    list_alternative3_distance.append(distance_plane/2)
            else:
                emission_train_w_bus = emission_train + emission_bus
                list_alternative_emissions.append(emission_train_w_bus/2)
                list_alternative_emissions_wo_bus.append(emission_train/2)
                list_alternative_time.append(time_train/2)
                list_alternative_distance.append(distance_train/2)
                if time_train < 2*3600*time_scenario2:
                    list_alternative2_emissions.append(emission_train_w_bus/2)
                    list_alternative2_emissions_wo_bus.append(emission_train/2)
                    list_alternative2_time.append(time_train/2)
                    list_alternative2_distance.append(distance_train/2)

                    list_alternative3_emissions.append(emission_train_w_bus/2)
                    list_alternative3_emissions_wo_bus.append(emission_train/2)
                    list_alternative3_time.append(time_train/2)
                    list_alternative3_distance.append(distance_train/2)
                
                elif time_train < 2*3600*time_scenario3:
                    list_alternative2_emissions.append((emission_plane+emission_bus)/2)
                    list_alternative2_emissions_wo_bus.append(emission_plane/2)
                    list_alternative2_time.append(time_plane/2)
                    list_alternative2_distance.append(distance_plane/2)

                    list_alternative3_emissions.append(emission_train_w_bus/2)
                    list_alternative3_emissions_wo_bus.append(emission_train/2)
                    list_alternative3_time.append(time_train/2)
                    list_alternative3_distance.append(distance_train/2)
                else:
                    list_alternative2_emissions.append((emission_plane+emission_bus)/2)
                    list_alternative2_emissions_wo_bus.append(emission_plane/2)
                    list_alternative2_time.append(time_plane/2)
                    list_alternative2_distance.append(distance_plane/2)

                    list_alternative3_emissions.append((emission_plane+emission_bus)/2)
                    list_alternative3_emissions_wo_bus.append(emission_plane/2)
                    list_alternative3_time.append(time_plane/2)
                    list_alternative3_distance.append(distance_plane/2)
        elif list_transport[k]=="train":
            list_alternative_emissions.append(list_emissions[k])
            list_alternative_emissions_wo_bus.append(list_emissions[k]-emission_bus/2)
            list_alternative_time.append(list_time[k])
            list_alternative_distance.append(list_distance[k])
            list_alternative2_emissions.append(list_emissions[k])
            list_alternative2_emissions_wo_bus.append(list_emissions[k]-emission_bus/2)
            list_alternative2_time.append(list_time[k])
            list_alternative2_distance.append(list_distance[k])
            list_alternative3_emissions.append(list_emissions[k])
            list_alternative3_emissions_wo_bus.append(list_emissions[k]-emission_bus/2)
            list_alternative3_time.append(list_time[k])
            list_alternative3_distance.append(list_distance[k])
        elif list_transport[k]=="bus":
            list_alternative_emissions.append(list_emissions[k])
            list_alternative_emissions_wo_bus.append(list_emissions[k])
            list_alternative_time.append(list_time[k])
            list_alternative_distance.append(list_distance[k])
            list_alternative2_emissions.append(list_emissions[k])
            list_alternative2_emissions_wo_bus.append(list_emissions[k])
            list_alternative2_time.append(list_time[k])
            list_alternative2_distance.append(list_distance[k])
            list_alternative3_emissions.append(list_emissions[k])
            list_alternative3_emissions_wo_bus.append(list_emissions[k])
            list_alternative3_time.append(list_time[k])
            list_alternative3_distance.append(list_distance[k])
        else:
            list_alternative_emissions.append(0)
            list_alternative_emissions_wo_bus.append(0)
            list_alternative_time.append(0)
            list_alternative_distance.append(0)

            list_alternative2_emissions.append(0)
            list_alternative2_emissions_wo_bus.append(0)
            list_alternative2_time.append(0)
            list_alternative2_distance.append(0)

            list_alternative3_emissions.append(0)
            list_alternative3_emissions_wo_bus.append(0)
            list_alternative3_time.append(0)
            list_alternative3_distance.append(0)

    # Create the final dataframe
    final_df = pd.DataFrame({})
    final_df["Id"]=list_id
    final_df["Visiting team"]=list_visiting_team
    final_df["Hosting team"]= list_hosting_team
    final_df["étape"]= list_aller_retour
    final_df["transport"]= list_transport
    final_df["emissions_kg_co2"] = list_emissions
    final_df["travel_time_seconds"] = list_time
    final_df["distance_km"] = list_distance
    final_df["alternative_emissions_kg_co2"] = list_alternative_emissions
    final_df["alternative_emissions_kg_co2_wo_empty_bus"] = (
        list_alternative_emissions_wo_bus
    )
    final_df["alternative_travel_time_seconds"] = list_alternative_time
    final_df["alternative_distance_km"] = list_alternative_distance
    final_df[f"alternative_emissions_kg_co2_scenario<{time_scenario2}"] = list_alternative2_emissions
    final_df[f"alternative_emissions_kg_co2_wo_empty_bus_scenario<{time_scenario2}"] = (
        list_alternative2_emissions_wo_bus
    )
    final_df[f"alternative_travel_time_seconds_scenario<{time_scenario2}"] = list_alternative2_time
    final_df[f"alternative_distance_km_scenario<{time_scenario2}"] = list_alternative2_distance

    final_df[f"alternative_emissions_kg_co2_scenario<{time_scenario3}"] = list_alternative3_emissions
    final_df[f"alternative_emissions_kg_co2_wo_empty_bus_scenario<{time_scenario3}"] = (
        list_alternative3_emissions_wo_bus
    )
    final_df[f"alternative_travel_time_seconds_scenario<{time_scenario3}"] = list_alternative3_time
    final_df[f"alternative_distance_km_scenario<{time_scenario3}"] = list_alternative3_distance

    final_df.to_csv(DATA_PATH + "total_emmissions_2.csv", index=False)


if __name__ == "__main__":
    main()
