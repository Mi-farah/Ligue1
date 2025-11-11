"""
Simplified service class for handling train journey calculations.

This service provides functionality to:
- Calculate train routes between stadiums using Google Maps transit API
- Compare train vs car emissions for optimal route selection
- Generate comprehensive carbon footprint analysis
"""

import os
import time
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ReadTimeout, RequestException
from tqdm import tqdm

from backend.global_variables import (
    DATA_PATH,
    NUMBER_OF_PASSENGERS,
    TRAIN_EMISSIONS_FILENAME,
)
from backend.services.base_transport_service import BaseTransportService, RouteData
from backend.services.car_service import CarTrajetService


class TrainTrajetService(BaseTransportService):
    """
    Simplified service class for handling train journey calculations.

    This service provides functionality to:
    - Calculate train routes between stadiums using Google Maps transit API
    - Compare train vs car emissions for optimal route selection
    - Generate comprehensive carbon footprint analysis
    """

    def __init__(self, api_key: str, sncf_api_key: str) -> None:
        """
        Initialize the TrainTrajetService with Google Maps API key.

        Args:
            api_key (str): Google Maps API key for geocoding and directions
        """
        super().__init__(api_key)
        self.sncf_api_key = sncf_api_key
        self.closest_station_cache = {}
        self._load_gare_positions_df()
        self.car_service = CarTrajetService(api_key)

        # Carbon emission constants (gCO2/passenger/km)
        self.number_of_passengers = (
            NUMBER_OF_PASSENGERS  # Number of passengers (team + staff)
        )

    def _load_gare_positions_df(self) -> None:
        if not os.path.exists(DATA_PATH + "gare_positions.csv"):
            self.logger.info("Gare positions file not found, starting geocoding...")
        self.gare_positions_df = pd.read_csv(DATA_PATH + "gare_positions.csv")
        self.logger.info(
            "Loaded %s gare positions from cache", len(self.gare_positions_df)
        )

    def _trip_stats(
        self, sections: list[dict[str, Any]], compute_using_google: bool = False
    ) -> dict[str, Any]:
        """Return totals + per-section breakdown:
        - total CO2 emissions (kgCO2)
        - total distance (km)
        - total time (s)
        - list of per-section stats with from/to

        Consecutive RER/Transilien sections are grouped and replaced with car routes.
        """
        total_co2 = 0.0
        total_dist = 0.0
        total_time = 0
        waiting_time = 0
        details = []

        corrected_sections = []
        for sec in sections:
            match sec.get("type"):
                case "crow_fly":
                    pass
                case "public_transport":
                    corrected_sections.append(sec)
                case "boarding":
                    waiting_time += sec.get("duration", 0)
                case "transfer":
                    waiting_time += sec.get("duration", 0)
                case "waiting":
                    waiting_time += sec.get("duration", 0)
                case _:
                    self.logger.warning("Unknown section type: %s", sec.get("type"))
                    corrected_sections.append(sec)

        i = 0
        while i < len(corrected_sections):
            sec = corrected_sections[i]
            physical_mode = sec.get("display_informations", {}).get("physical_mode")

            if physical_mode == "RER / Transilien":
                # Group consecutive RER/Transilien sections
                rer_group = [sec]
                j = i + 1
                while j < len(corrected_sections):
                    next_sec = corrected_sections[j]
                    next_physical_mode = next_sec.get("display_informations", {}).get(
                        "physical_mode"
                    )
                    if next_physical_mode == "RER / Transilien":
                        rer_group.append(next_sec)
                        j += 1
                    else:
                        break

                # Get coordinates from first section's "from" and last section's "to"
                first_sec = rer_group[0]
                last_sec = rer_group[-1]

                from_coord = first_sec["geojson"]["coordinates"][
                    0
                ]  # lon, lat in SNCF api
                to_coord = last_sec["geojson"]["coordinates"][
                    -1
                ]  # lon, lat in SNCF api

                from_name = first_sec.get("from", {}).get("name", "")
                to_name = last_sec.get("to", {}).get("name", "")
                departure_coords = (
                    float(from_coord[1]),
                    float(from_coord[0]),
                )  # lat, lon
                arrival_coords = (
                    float(to_coord[1]),
                    float(to_coord[0]),
                )  # lat, lon

                if compute_using_google:
                    car_route = self.car_service.calculate_route(
                        departure=from_name,
                        arrival=to_name,
                        departure_coords=departure_coords,
                        arrival_coords=arrival_coords,
                        round_trip=False,
                    )
                else:
                    approximate_distance_km = self.calculate_distance(
                        departure_coords[0],
                        departure_coords[1],
                        arrival_coords[0],
                        arrival_coords[1],
                    )
                    approximate_travel_time_seconds = (
                        approximate_distance_km * 3600 / 50
                    )  # 50 km/h
                    emissions = self.car_service.calculate_emissions(
                        approximate_distance_km
                    )
                    car_route = RouteData(
                        departure=from_name,
                        arrival=to_name,
                        travel_time_seconds=approximate_travel_time_seconds,
                        distance_km=approximate_distance_km,
                        emissions_kg_co2=emissions,
                        transport_type="car",
                        route_details=None,
                    )
                total_time += car_route.travel_time_seconds
                total_dist += car_route.distance_km
                total_co2 += car_route.emissions_kg_co2

                details.append(
                    {
                        "from": from_name,
                        "to": to_name,
                        "type": "car",
                        "distance_km": car_route.distance_km,
                        "co2_kg": car_route.emissions_kg_co2,
                        "time_s": car_route.travel_time_seconds,
                    }
                )

                # Skip all sections in the group
                i = j
            else:
                # Process non-RER/Transilien sections normally
                sec_time = sec.get("duration", 0)
                sec_dist = (
                    sec.get("geojson", {}).get("properties", [{}])[0].get("length", 0)
                    / 1000.0
                )  # m → km
                sec_co2 = (
                    sec.get("co2_emission", {}).get("value", 0.0) / 1000.0
                )  # g → kg

                # Update totals
                total_time += sec_time
                total_dist += sec_dist
                total_co2 += sec_co2

                # Names (fallback to empty string if missing)
                from_name = sec.get("from", {}).get("name", "")
                to_name = sec.get("to", {}).get("name", "")

                # Save section detail
                if sec_dist > 0:
                    details.append(
                        {
                            "from": from_name,
                            "to": to_name,
                            "type": sec.get("type", "unknown"),
                            "distance_km": sec_dist,
                            "co2_kg": sec_co2,
                            "time_s": sec_time,
                        }
                    )
                i += 1

        return {
            "carbon_emission_kgCO2": total_co2,
            "distance_km": total_dist,
            "duration_s": total_time + waiting_time,
            "details": details,
        }

    def _get_sncf_journeys(
        self,
        from_id: str,
        to_id: str,
        start_date: datetime,
        n_days: int,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        url = "https://api.sncf.com/v1/coverage/sncf/journeys"
        week_trains = []
        date_query = start_date

        for _ in range(n_days):
            params = {
                "from": from_id,
                "to": to_id,
                "datetime": date_query.strftime("%Y%m%dT%H%M%S"),
            }

            # Retry logic with exponential backoff
            retries = 0
            while retries <= max_retries:
                try:
                    r = requests.get(
                        url,
                        params=params,
                        auth=HTTPBasicAuth(self.sncf_api_key, ""),
                        timeout=60,  # Increased timeout to 60 seconds
                    )
                    r.raise_for_status()  # Raise an exception for bad status codes
                    data = r.json()
                    journeys = data.get("journeys", [])
                    for j in journeys:
                        week_trains.append(j)
                    break  # Success, exit retry loop

                except (ReadTimeout, RequestException) as e:
                    retries += 1
                    if retries > max_retries:
                        self.logger.error(
                            "SNCF API request failed after %d retries for %s -> %s on %s: %s",
                            max_retries,
                            from_id,
                            to_id,
                            date_query.strftime("%Y%m%dT%H%M%S"),
                            e,
                        )
                        # Continue to next day instead of failing completely
                        break
                    else:
                        wait_time = 2**retries  # Exponential backoff: 2, 4, 8 seconds
                        self.logger.warning(
                            "SNCF API request failed (attempt %d/%d): %s. Retrying in %d seconds...",
                            retries,
                            max_retries,
                            e,
                            wait_time,
                        )
                        time.sleep(wait_time)

            # move to next day at 00:00
            date_query += timedelta(days=1)
        return week_trains

    def _calculate_car_part(
        self,
        departure: str,
        arrival: str,
        departure_stop_area_id: str,
        arrival_stop_area_id: str,
    ) -> RouteData:
        """
        Calculate the total distance and duration (round trip) by car for:
        - Stadium to departure station
        - Arrival station to stadium

        departure : city name
        arrival : city name
        departure_stop_area_id : stop area id
        arrival_stop_area_id : stop area id

        Returns:
            RouteData object (empty if calculation fails)
        """
        gare_departure_row = self.gare_positions_df.loc[
            self.gare_positions_df["stop_area_id"] == departure_stop_area_id
        ].to_dict(orient="records")[0]
        gare_arrival_row = self.gare_positions_df.loc[
            self.gare_positions_df["stop_area_id"] == arrival_stop_area_id
        ].to_dict(orient="records")[0]

        departure_stadium_latitude, departure_stadium_longitude = self.stadium_df.loc[
            self.stadium_df["Stadium"] == gare_departure_row["stadium_name"],
            ["latitude", "longitude"],
        ].iloc[0]
        arrival_stadium_latitude, arrival_stadium_longitude = self.stadium_df.loc[
            self.stadium_df["Stadium"] == gare_arrival_row["stadium_name"],
            ["latitude", "longitude"],
        ].iloc[0]

        departure_stadium_coords = (
            departure_stadium_latitude,
            departure_stadium_longitude,
        )
        arrival_stadium_coords = (arrival_stadium_latitude, arrival_stadium_longitude)

        # Use CarTrajetService to calculate RouteData for each car segment, sum for round trip
        car_leg_1 = self.car_service.calculate_route(
            departure=gare_departure_row["stadium_name"],
            arrival=gare_departure_row["gare_name"],
            departure_coords=departure_stadium_coords,
            arrival_coords=(
                gare_departure_row["latitude"],
                gare_departure_row["longitude"],
            ),
            round_trip=True,
        )
        car_leg_2 = self.car_service.calculate_route(
            departure=gare_arrival_row["stadium_name"],
            arrival=gare_arrival_row["gare_name"],
            departure_coords=arrival_stadium_coords,
            arrival_coords=(
                gare_arrival_row["latitude"],
                gare_arrival_row["longitude"],
            ),
            round_trip=True,
        )

        # Calculate totals for round trip (2x both legs)
        if car_leg_1 and car_leg_2:
            total_distance = car_leg_1.distance_km + car_leg_2.distance_km
            total_duration = (
                car_leg_1.travel_time_seconds + car_leg_2.travel_time_seconds
            )
            total_emissions = car_leg_1.emissions_kg_co2 + car_leg_2.emissions_kg_co2
            all_details = {
                "segments": [
                    {
                        "from": gare_departure_row["stadium_name"],
                        "to": gare_departure_row["gare_name"],
                        "distance_km": car_leg_1.distance_km,
                        "travel_time_seconds": car_leg_1.travel_time_seconds,
                        "emissions_kg_co2": car_leg_1.emissions_kg_co2,
                    },
                    {
                        "from": gare_arrival_row["gare_name"],
                        "to": gare_arrival_row["stadium_name"],
                        "distance_km": car_leg_2.distance_km,
                        "travel_time_seconds": car_leg_2.travel_time_seconds,
                        "emissions_kg_co2": car_leg_2.emissions_kg_co2,
                    },
                ]
            }
            return RouteData(
                departure=departure,
                arrival=arrival,
                travel_time_seconds=total_duration,
                distance_km=total_distance,
                emissions_kg_co2=total_emissions,
                transport_type="car",
                route_details=all_details,
            )
        else:
            return RouteData(
                departure=departure,
                arrival=arrival,
                travel_time_seconds=0,
                distance_km=0,
                emissions_kg_co2=0,
                transport_type="car",
                route_details={"car_route_details": "Car part could not be calculated"},
            )

    def calculate_route(
        self,
        departure: str,
        arrival: str,
        departure_coords: Tuple[float, float],
        arrival_coords: Tuple[float, float],
    ) -> Optional[RouteData]:
        """
        Calculate train route between two stadiums.

        Args:
            departure: Departure team name
            arrival: Arrival team name
            departure_coords: Departure coordinates (lat, lng)
            arrival_coords: Arrival coordinates (lat, lng)

        Returns:
            RouteData object or None if calculation fails
        """
        # get closest stations
        stop_area_departures: List[str] = self.gare_positions_df[
            self.gare_positions_df["team_name"] == departure
        ]["stop_area_id"].tolist()
        stop_area_arrivals: List[str] = self.gare_positions_df[
            self.gare_positions_df["team_name"] == arrival
        ]["stop_area_id"].tolist()
        self.logger.debug("departure: %s", departure)
        self.logger.debug("stop_area_departures: %s", stop_area_departures)
        self.logger.debug("arrival: %s", arrival)
        self.logger.debug("stop_area_arrivals: %s", stop_area_arrivals)

        week_trains = []
        for stop_area_departure in tqdm(stop_area_departures):
            for stop_area_arrival in stop_area_arrivals:
                new_week_trains = self._get_sncf_journeys(
                    stop_area_departure,
                    stop_area_arrival,
                    datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
                    + timedelta(days=2),
                    3,
                )
                new_week_trains = [
                    {
                        "stop_area_departure_id": stop_area_departure,
                        "stop_area_arrival_id": stop_area_arrival,
                    }
                    | week_train
                    for week_train in new_week_trains
                ]
                week_trains.extend(new_week_trains)
        if not week_trains:
            self.logger.info("No train route found for %s to %s...", departure, arrival)
            return RouteData(
                departure=departure,
                arrival=arrival,
                travel_time_seconds=0,
                distance_km=0,
                emissions_kg_co2=0,
                transport_type="train",
                route_details={"train_route_details": "No train route found"},
            )

        # train part
        fastest_train = min(
            week_trains,
            key=lambda train: self._trip_stats(
                train["sections"], compute_using_google=False
            )["duration_s"],
        )
        fastest_train_route = self._trip_stats(
            fastest_train["sections"], compute_using_google=True
        )

        # car part
        car_route: RouteData = self._calculate_car_part(
            departure,
            arrival,
            fastest_train["stop_area_departure_id"],
            fastest_train["stop_area_arrival_id"],
        )
        return RouteData(
            departure=departure,
            arrival=arrival,
            travel_time_seconds=fastest_train_route["duration_s"] * 2
            + car_route.travel_time_seconds,
            distance_km=fastest_train_route["distance_km"] * 2 + car_route.distance_km,
            emissions_kg_co2=fastest_train_route["carbon_emission_kgCO2"]
            * 2
            * self.number_of_passengers
            + car_route.emissions_kg_co2,  # Round trip
            transport_type="train",
            route_details={
                "train_route_details": fastest_train_route["details"],
                "car_route_details": car_route.route_details,
            },
        )

    def run_complete_analysis(
        self, output_filename: str = TRAIN_EMISSIONS_FILENAME
    ) -> List[RouteData]:
        """
        Run the complete analysis pipeline.

        Args:
            output_filename: Name of the output CSV file

        Returns:
            List of RouteData objects
        """
        self.logger.debug("Running complete analysis...")
        self.logger.debug("output_filename: %s", output_filename)
        super().run_complete_analysis(output_filename)
