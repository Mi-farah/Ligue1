from typing import List, Tuple, Optional, Dict, Any
import requests
from requests.auth import HTTPBasicAuth
from backend.global_variables import TRAIN_EMISSIONS_FILENAME, NUMBER_OF_PASSENGERS
from backend.services.base_transport_service import BaseTransportService, RouteData
from datetime import timedelta, datetime

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

        # Carbon emission constants (gCO2/passenger/km)
        self.number_of_passengers = NUMBER_OF_PASSENGERS  # Number of passengers (team + staff)


    def _get_closest_station(self, city_query: str, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
            """
            Returns the closest SNCF train station stop_area id given a latitude and longitude.
            """
            # check if station is already in cache
            if city_query in self.closest_station_cache:
                return self.closest_station_cache[city_query]
            
            # if not, get closest station
            url = "https://api.sncf.com/v1/coverage/sncf/places"
            params = {"q": city_query}
            response = requests.get(url, params=params, auth=HTTPBasicAuth(self.sncf_api_key, ""), timeout=30)
            data = response.json()
            places = data.get("places", [])
            if not places:
                print(f"WARNING: No station found for {city_query}")
                return None, None
            closest_place = None
            min_distance = float('inf')
            for place in places:
                if "stop_area" in place["id"]:
                    place_lat = float(place["stop_area"]["coord"]["lat"])
                    place_lon = float(place["stop_area"]["coord"]["lon"])
                    distance = self.calculate_distance(lat, lon, place_lat, place_lon)
                    print(f"distance: {distance} from {city_query} to {place['stop_area']['name']}")
                    if distance < min_distance:
                        min_distance = distance
                        closest_place = place
            if closest_place:
                stop_area_id = closest_place["stop_area"]["id"]
                stop_area_name = closest_place["stop_area"]["name"]
                self.closest_station_cache[city_query] = (stop_area_id, stop_area_name)
            else:
                print(f"WARNING: No station found for {city_query}")
                return None, None
            self.closest_station_cache[city_query] = (stop_area_id, stop_area_name)
            return stop_area_id, stop_area_name
    
    def _compute_section_distance(self, sec:dict[str, Any]):
        """Compute distance of a section from geojson coordinates (km)."""
        coords = sec.get("geojson", {}).get("coordinates", [])
        if len(coords) < 2:
            return 0.0
        dist = 0.0
        for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
            dist += self.calculate_distance(lat1, lon1, lat2, lon2)
        return dist

    def _trip_stats(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        """Return totals + per-section breakdown:
        - total CO2 emissions (kgCO2)
        - total distance (km)
        - total time (s)
        - list of per-section stats with from/to
        """
        total_co2 = 0.0
        total_dist = 0.0
        total_time = 0
        details = []

        for sec in sections:
            sec_time = sec.get("duration", 0)
            sec_dist = self._compute_section_distance(sec)
            sec_co2 = sec.get("co2_emission", {}).get("value", 0.0) / 1000.0  # g → kg

            # Update totals
            total_time += sec_time
            total_dist += sec_dist
            total_co2 += sec_co2

            # Names (fallback to empty string if missing)
            from_name = sec.get("from", {}).get("name", "")
            to_name = sec.get("to", {}).get("name", "")

            # Save section detail
            if sec_dist > 0:
                details.append({
                    "from": from_name,
                    "to": to_name,
                    "type": sec.get("type", "unknown"),
                    "distance_km": sec_dist,
                    "co2_kg": sec_co2,
                    "time_s": sec_time
                })
        return {"carbon_emission_kgCO2": total_co2, "distance_km": total_dist, "duration_s": total_time, "details": details}
    
    def _get_week_journeys(self, from_id: str, to_id: str, start_date: datetime) -> list[dict[str, Any]]:
        url = "https://api.sncf.com/v1/coverage/sncf/journeys"
        week_trains = []
        dt = start_date

        for _ in range(7):  # 7 days
            params = {
                "from": from_id,
                "to": to_id,
                "datetime": dt.strftime("%Y%m%dT%H%M%S")
            }
            r = requests.get(url, params=params, auth=HTTPBasicAuth(self.sncf_api_key, ""), timeout=30)
            data = r.json()
            journeys = data.get("journeys", [])
            for j in journeys:
                week_trains.append(j)
            # move to next day at 00:00
            dt += timedelta(days=1)
        return week_trains

    
    def calculate_route(self, departure: str, arrival: str, departure_coords: Tuple[float, float], 
                       arrival_coords: Tuple[float, float]) -> Optional[RouteData]:
        """
        Calculate train route between two stadiums.
        
        Args:
            departure: Departure stadium name
            arrival: Arrival stadium name
            departure_coords: Departure coordinates (lat, lng)
            arrival_coords: Arrival coordinates (lat, lng)
            
        Returns:
            RouteData object or None if calculation fails
        """
        # get closest station
        origin_id, _ = self._get_closest_station(departure, departure_coords[0], departure_coords[1])
        destination_id, _ = self._get_closest_station(arrival, arrival_coords[0], arrival_coords[1])
        
        # Get train route using transit mode
        print(origin_id, destination_id)
        week_trains = self._get_week_journeys(origin_id, destination_id, datetime.now() + timedelta(days=1))
        if week_trains:
            fastest_train = min(week_trains, key=lambda train: self._trip_stats(train["sections"])["duration_s"])
            fastest_train_route = self._trip_stats(fastest_train["sections"])
            print(fastest_train_route['duration_s']*2)
            return RouteData(
                departure=departure,
                arrival=arrival,
                travel_time_seconds=fastest_train_route['duration_s']*2,
                distance_km=fastest_train_route['distance_km']*2,
                emissions_kg_co2=fastest_train_route['carbon_emission_kgCO2']*2*self.number_of_passengers,  # Round trip
                transport_type="train",
                route_details={"train_route_details":fastest_train_route["details"]},
            )
        else:
            print(f"No train route found for {departure} to {arrival}...")
            return RouteData(
                departure=departure,
                arrival=arrival,
                travel_time_seconds=0,
                distance_km=0,
                emissions_kg_co2=0,
                transport_type="train",
                route_details={"train_route_details":"No train route found"},
            )

    def run_complete_analysis(self, output_filename: str = TRAIN_EMISSIONS_FILENAME) -> List[RouteData]:
        """
        Run the complete analysis pipeline.
        
        Args:
            output_filename: Name of the output CSV file
            
        Returns:
            List of RouteData objects
        """
        super().run_complete_analysis(output_filename)