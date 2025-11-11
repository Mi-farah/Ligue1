"""
Service for calculating car travel routes, distances, and carbon emissions between stadiums.
"""

from typing import Optional, Tuple

from backend.global_variables import (
    AUTO_CAR_EMISSION_FACTOR,
    CAR_EMISSIONS_FILENAME,
    NUMBER_OF_PASSENGERS,
)
from backend.services.base_transport_service import BaseTransportService, RouteData


class CarTrajetService(BaseTransportService):
    """
    Service for calculating car travel routes, distances, and carbon emissions between stadiums.

    Source: https://bigmedia.bpifrance.fr/nos-dossiers/empreinte-carbone-des-trajets-en-train-calcul-et-decarbonation
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.number_of_passengers = (
            NUMBER_OF_PASSENGERS  # Number of passengers (team + staff)
        )
        self.autocar_emission_factor = AUTO_CAR_EMISSION_FACTOR  # kgCO2/passenger/km

    def calculate_emissions(self, distance_km: float) -> float:
        """Calculate emissions for a given distance in kilometers."""
        return self.autocar_emission_factor * distance_km * self.number_of_passengers

    def calculate_route(
        self,
        departure: str,
        arrival: str,
        departure_coords: Tuple[float, float],
        arrival_coords: Tuple[float, float],
        round_trip: bool = True,
    ) -> Optional[RouteData]:
        """
        Calculate car route between two stadiums.

        Args:
            departure: Departure stadium name
            arrival: Arrival stadium name
            departure_coords: Departure coordinates (lat, lng)
            arrival_coords: Arrival coordinates (lat, lng)

        Returns:
            RouteData object or None if calculation fails
        """
        origin_coords = self._format_coordinates(
            departure_coords[0], departure_coords[1]
        )
        destination_coords = self._format_coordinates(
            arrival_coords[0], arrival_coords[1]
        )

        distance_km, duration_seconds = self._get_road_distance_duration(
            origin_coords, destination_coords
        )
        if distance_km is not None and duration_seconds is not None:
            # Calculate emissions with round trip multiplier
            emissions = self.calculate_emissions(distance_km)  # kg of CO2
            multiplier = 2 if round_trip else 1
            return RouteData(
                departure=departure,
                arrival=arrival,
                travel_time_seconds=duration_seconds * multiplier,
                distance_km=distance_km * multiplier,
                emissions_kg_co2=emissions * multiplier,
                transport_type="car",
                route_details={
                    "one_way_distance_km": distance_km,
                    "one_way_duration_seconds": duration_seconds,
                    "one_way_emissions_kg_co2": emissions,
                    "travel_steps": [
                        {
                            "step_type": "car",
                            "from": departure,
                            "to": arrival,
                            "distance_km": distance_km,
                            "travel_time_seconds": duration_seconds,
                        },
                        {
                            "step_type": "car",
                            "from": arrival,
                            "to": departure,
                            "distance_km": distance_km,
                            "travel_time_seconds": duration_seconds,
                        },
                    ],
                },
            )

        else:
            return RouteData(
                departure=departure,
                arrival=arrival,
                travel_time_seconds=0,
                distance_km=0,
                emissions_kg_co2=0,
                transport_type="car",
                route_details={"car_route_details": "No car route found"},
            )

    def run_complete_analysis(
        self, output_filename: str = CAR_EMISSIONS_FILENAME
    ) -> None:
        """Run the complete analysis pipeline."""
        super().run_complete_analysis(output_filename)
