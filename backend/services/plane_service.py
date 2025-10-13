import pandas as pd
import os
from typing import Tuple, Optional, Dict
from backend.global_variables import FLIGHT_EMISSIONS_FILENAME, DATA_PATH, AIRPORT_CACHE_FILENAME, AUTO_CAR_EMISSION_FACTOR, NUMBER_OF_PASSENGERS
from backend.services.base_transport_service import BaseTransportService, RouteData

class PlaneTrajetService(BaseTransportService):
    def __init__(self, api_key: str) -> None:
        super().__init__(api_key)
        self.airport_keywords = ['airport', "Airport", "Aeroport", "Aéroport", 'aéroport', 'aeroport']
        
        # Airport cache to avoid recomputing nearest airports
        self.airport_cache: Dict[str, Dict] = {}
        self._load_airport_cache()
        
        # Constants for emissions calculations
        self.number_of_passengers = NUMBER_OF_PASSENGERS  # Number of passengers (team + staff)
        self.autocar_emission_factor = AUTO_CAR_EMISSION_FACTOR  # kgCO2/passenger/km
        self.jet_fuel_to_co2 = 3.15  # kgCO2/kg of jet fuel (https://www.carbonindependent.org/files/B851vs2.4.pdf, page 22)

        # Fuel consumption coefficients (from regression analysis based on ERJ145 data)
        self.fuel_consumption_coef = 1.2174  # kg/km
        self.fuel_consumption_intercept = 282.8615  # kg
        
        # Time calculation coefficients (Not checked yet)
        self.time_plane_coef = 0.00120352141554664 # h/km
        self.time_plane_intercept = 0.285387849787546 # h

        # Multiplication factor for other then fuel emission of plane (https://bigmedia.bpifrance.fr/sites/default/files/inline-images/sncf%202.png)
        self.multiplication_factor_other_than_fuel = 260/141

    def is_real_airport(self, place_name: str) -> bool:
        """Check if a place name contains airport-related keywords."""
        return any(keyword.lower() in place_name.lower() for keyword in self.airport_keywords)

    def _load_airport_cache(self) -> None:
        """Load airport cache from CSV file if it exists."""
        cache_file_path = DATA_PATH + AIRPORT_CACHE_FILENAME
        if os.path.exists(cache_file_path):
            try:
                df = pd.read_csv(cache_file_path)
                for _, row in df.iterrows():
                    coord_key = f"{row['latitude']:.3f},{row['longitude']:.3f}"
                    self.airport_cache[coord_key] = {
                        "name": row['name'],
                        "latitude": row['latitude'],
                        "longitude": row['longitude']
                    }
                self.logger.info(f"Loaded {len(self.airport_cache)} airports from cache")
            except Exception as e:
                self.logger.error(f"Error loading airport cache: {e}")
                self.airport_cache = {}

    def _save_airport_cache(self) -> None:
        """Save airport cache to CSV file."""
        if not self.airport_cache:
            return
            
        cache_file_path = DATA_PATH + AIRPORT_CACHE_FILENAME
        try:
            # Create DataFrame from cache
            cache_data = []
            for _, airport_data in self.airport_cache.items():
                cache_data.append({
                    'latitude': airport_data['latitude'],
                    'longitude': airport_data['longitude'],
                    'name': airport_data['name']
                })
            
            df = pd.DataFrame(cache_data)
            df.to_csv(cache_file_path, index=False)
        except Exception as e:
            self.logger.error("Error saving airport cache: %s", e)

    def _get_cache_key(self, lat: float, lon: float) -> str:
        """Generate cache key for coordinates (rounded to 6 decimal places)."""
        return f"{lat:.3f},{lon:.3f}"


    def get_cache_stats(self) -> dict:
        """Get statistics about the airport cache."""
        return {
            "cached_airports": len(self.airport_cache),
            "cache_file_exists": os.path.exists(DATA_PATH + AIRPORT_CACHE_FILENAME)
        }

    def get_nearest_airport(self, lat: float, lon: float) -> dict:
        """Find the nearest airport to given coordinates, using cache when possible."""
        # Check cache first
        cache_key = self._get_cache_key(lat, lon)
        if cache_key in self.airport_cache:
            return self.airport_cache[cache_key]
        
        # If not in cache, make API request
        params = {
            "location": f"{lat},{lon}",
            "radius": 50000,
            "type": "airport",
            "key": self.api_key
        }
        data = self._make_google_maps_request("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params)
        if data and data.get("status") == "OK" and data.get("results"):
            # Find the first valid airport
            valid_result = next(
                (place for place in data["results"] if self.is_real_airport(place["name"])),
                None
            )

            if valid_result:
                airport_data = {
                    "name": valid_result["name"],
                    "latitude": valid_result["geometry"]["location"]["lat"],
                    "longitude": valid_result["geometry"]["location"]["lng"]
                }
                # Add to cache and save
                self.airport_cache[cache_key] = airport_data
                self._save_airport_cache()
                
                return airport_data
            else:
                return {"error": "No real airport found in results"}
        else:
            return {"error": data.get("status", "No results") if data else "Request failed"}


    def calculate_fuel_consumption(self, distance: float) -> float:
        """Calculate fuel consumption based on distance using regression coefficients."""
        return self.fuel_consumption_coef * distance + self.fuel_consumption_intercept

    def calculate_flight_time(self, distance: float) -> int:
        """Calculate flight time in seconds based on distance."""
        time_in_hours = self.time_plane_coef * distance + self.time_plane_intercept
        hours = int(time_in_hours)
        minutes = (time_in_hours - hours) * 60
        return int(hours * 3600 + minutes * 60)


    def calculate_route(self, departure: str, arrival: str, departure_coords: Tuple[float, float], 
                       arrival_coords: Tuple[float, float]) -> Optional[RouteData]:
        """
        Calculate plane route between two stadiums.
        
        Args:
            departure: Departure stadium name
            arrival: Arrival stadium name
            departure_coords: Departure coordinates (lat, lng)
            arrival_coords: Arrival coordinates (lat, lng)
            
        Returns:
            RouteData object or None if calculation fails
        """
        # Get nearest airports for both stadiums
        departure_airport = self.get_nearest_airport(departure_coords[0], departure_coords[1])
        arrival_airport = self.get_nearest_airport(arrival_coords[0], arrival_coords[1])
        
        if "error" in departure_airport or "error" in arrival_airport:
            return None
        
        # Calculate flight distance and time
        flight_distance = self.calculate_distance(
            departure_airport["latitude"], departure_airport["longitude"],
            arrival_airport["latitude"], arrival_airport["longitude"]
        ) * 2
        flight_time = self.calculate_flight_time(flight_distance)
        # Calculate autocar distances and times
        stadium_to_airport_origin = self._format_coordinates(departure_coords[0], departure_coords[1])
        stadium_to_airport_dest = self._format_coordinates(departure_airport["latitude"], departure_airport["longitude"])
        distance_autocar_dep, time_autocar_dep = self._get_road_distance_duration(
            stadium_to_airport_origin, stadium_to_airport_dest
        )
        
        airport_to_stadium_origin = self._format_coordinates(arrival_airport["latitude"], arrival_airport["longitude"])
        airport_to_stadium_dest = self._format_coordinates(arrival_coords[0], arrival_coords[1])
        distance_autocar_arr, time_autocar_arr = self._get_road_distance_duration(
            airport_to_stadium_origin, airport_to_stadium_dest
        )
        
        distance_autocar_dep = distance_autocar_dep if distance_autocar_dep else 0
        time_autocar_dep = time_autocar_dep if time_autocar_dep else 0
        distance_autocar_arr = distance_autocar_arr if distance_autocar_arr else 0
        time_autocar_arr = time_autocar_arr if time_autocar_arr else 0
        added_details = ""
        added_details += "No autocar departure route found" if not distance_autocar_dep else ""
        added_details += "No autocar arrival route found" if not distance_autocar_arr else ""
        
        # Calculate total distance and time
        total_distance = flight_distance + distance_autocar_dep + distance_autocar_arr
        total_time = flight_time + time_autocar_dep + time_autocar_arr
        
        # Calculate emissions
        fuel_consumption = self.calculate_fuel_consumption(flight_distance)
        plane_emission = self.jet_fuel_to_co2 * fuel_consumption * self.multiplication_factor_other_than_fuel
        autocar_emission = self.autocar_emission_factor * self.number_of_passengers * (distance_autocar_dep + distance_autocar_arr)

        # Total emissions (round trip)
        total_emissions = (plane_emission + autocar_emission) # kg of CO2
        
        return RouteData(
            departure=departure,
            arrival=arrival,
            travel_time_seconds=total_time,
            distance_km=total_distance,
            emissions_kg_co2=total_emissions,
            transport_type="plane",
            route_details={
                "flight_distance_km": flight_distance,
                "flight_time_seconds": flight_time,
                "autocar_distance_km": distance_autocar_dep + distance_autocar_arr,
                "autocar_time_seconds": time_autocar_dep + time_autocar_arr,
                "fuel_consumption_kg": fuel_consumption,
                "plane_emission_kg_co2": plane_emission,
                "autocar_emission_kg_co2": autocar_emission,
                "added_details": added_details
            }
        )

    def run_complete_analysis(self, output_filename: str = FLIGHT_EMISSIONS_FILENAME) -> None:
        """
        Run the complete analysis pipeline.
        
        Args:
            output_filename: Name of the output CSV file
            
        Returns:
            List of RouteData objects
        """
        super().run_complete_analysis(output_filename)
