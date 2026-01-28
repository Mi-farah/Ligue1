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
    data_historic_travels,
    id_vars=["v"],
    var_name="hosting_team",
    value_name="transport_type",
)

reconstructed_data = reconstructed_data.rename(columns={"v": "visiting_team"})


def get_emissions_and_time(
    visiting_team_name: str, hosting_team_name: str, transport_type: str
) -> Tuple[float, float, float]:
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
        return (
            subset2["emissions_kg_co2"].iloc[0],
            subset2["travel_time_seconds"].iloc[0],
            subset2["distance_km"].iloc[0],
        )
    else:
        return (
            subset["emissions_kg_co2"].iloc[0],
            subset["travel_time_seconds"].iloc[0],
            subset["distance_km"].iloc[0],
        )


def main():
    """
    Calculate the emissions and time for each transport mode.
    """
    # Calculate the emissions and time for each transport mode
    list_emissions_wo_empty_bus: list[float] = []
    list_emissions: list[float] = []
    list_time: list[float] = []
    list_distance: list[float] = []
    list_transport_type: list[str] = []
    for _, row in reconstructed_data.iterrows():
        visiting_team = row["visiting_team"]
        hosting_team = row["hosting_team"]
        transport = row["transport_type"]

        emission_wo_empty_bus, time, distance = get_emissions_and_time(
            visiting_team, hosting_team, transport.lower()
        )

        # if the transport is not bus, we add the emissions of the bus for the empty bus trip
        if transport != "bus" and visiting_team != hosting_team:
            emission_bus, _, _ = get_emissions_and_time(
                visiting_team, hosting_team, "bus".lower()
            )
            emission = emission_wo_empty_bus + emission_bus
        else:
            emission = emission_wo_empty_bus

        list_time.append(time)
        list_distance.append(distance)
        list_transport_type.append(transport.lower())
        list_emissions_wo_empty_bus.append(emission_wo_empty_bus)
        list_emissions.append(emission)

    # Calculate the alternative emissions and time
    list_alternative_emissions = []
    list_alternative_distance = []
    list_alternative_transport_type = []
    list_alternative_time = []
    list_alternative_emissions_wo_bus = []
    for _, row in reconstructed_data.iterrows():
        visiting_team = row["visiting_team"]
        hosting_team = row["hosting_team"]

        if visiting_team != hosting_team:
            emission_train, time_train, distance_train = get_emissions_and_time(
                visiting_team, hosting_team, "train"
            )
            emission_bus, time_bus, distance_bus = get_emissions_and_time(
                visiting_team, hosting_team, "bus"
            )

            if time_bus < time_train:
                list_alternative_emissions.append(emission_bus)
                list_alternative_emissions_wo_bus.append(emission_bus)
                list_alternative_time.append(time_bus)
                list_alternative_distance.append(distance_bus)
                list_alternative_transport_type.append("bus")
            # If the time of the train is less than the time of the bus, add the emissions and time of the bus
            # we prefer the train, and add the emissions of the bus for the empty bus trip
            else:
                emission_train_w_bus = emission_train + emission_bus
                list_alternative_emissions.append(emission_train_w_bus)
                list_alternative_emissions_wo_bus.append(emission_train)
                list_alternative_time.append(time_train)
                list_alternative_distance.append(distance_train)
                list_alternative_transport_type.append("train")
        else:
            list_alternative_emissions.append(0)
            list_alternative_emissions_wo_bus.append(0)
            list_alternative_time.append(0)
            list_alternative_distance.append(0)
            list_alternative_transport_type.append(None)

    # Create the final dataframe
    final_df = reconstructed_data.copy()
    final_df["emissions_kg_co2"] = list_emissions
    final_df["emissions_kg_co2_wo_empty_bus"] = list_emissions_wo_empty_bus
    final_df["travel_time_seconds"] = list_time
    final_df["distance_km"] = list_distance
    final_df["transport_type"] = list_transport_type
    final_df["alternative_emissions_kg_co2"] = list_alternative_emissions
    final_df["alternative_emissions_kg_co2_wo_empty_bus"] = (
        list_alternative_emissions_wo_bus
    )
    final_df["alternative_travel_time_seconds"] = list_alternative_time
    final_df["alternative_distance_km"] = list_alternative_distance
    final_df["alternative_transport_type"] = list_alternative_transport_type

    final_df.to_csv(DATA_PATH + "total_emissions.csv", index=False)


if __name__ == "__main__":
    main()
