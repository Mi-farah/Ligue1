"""
Base class for all transport services (train, plane, car).

This class provides common functionality and enforces a consistent
interface across all transport services. It handles:
- Google Maps API interactions
- Stadium data loading and processing
- Common route calculations
- Standardized data structures
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from backend.global_variables import (
    DATA_PATH,
    LOCALISATION_STADE_FILENAME,
    NAME_STADE_FILENAME,
    ROAD_DISTANCE_CACHE_FILENAME,
    GoogleMapsUrls,
)


@dataclass
class RouteData:
    """
    Standardized data structure for transport routes.

    This dataclass provides a common format for all transport services
    to ensure consistency across train, plane, and car calculations.
    """

    departure: str
    arrival: str
    travel_time_seconds: int  # in seconds
    distance_km: float  # in kilometers
    emissions_kg_co2: float  # in kg CO2
    transport_type: str  # "train", "plane", "car"
    route_details: Optional[Dict[str, Any]] = None  # Additional route-specific data


class BaseTransportService(ABC):
    """
    Base class for all transport services (train, plane, car).

    This class provides common functionality and enforces a consistent
    interface across all transport services. It handles:
    - Google Maps API interactions
    - Stadium data loading and processing
    - Common route calculations
    - Standardized data structures
    """

    def __init__(self, api_key: str):
        """
        Initialize the base transport service.

        Args:
            api_key: Google Maps API key
        """
        self.api_key = api_key
        self.console = Console()

        # Setup rich logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True)],
        )
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize road distance cache
        self.road_distance_cache = {}
        self._load_stadium_data()
        self._load_road_distance_cache()

    def _make_google_maps_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to Google Maps API with error handling.

        Args:
            url: API endpoint URL
            params: Request parameters for GET requests
            json_data: JSON body for POST requests
            headers: Optional HTTP headers
            method: HTTP method ("GET" or "POST")

        Returns:
            API response data or None if request fails
        """
        try:
            self.logger.debug("Making Google Maps API request to: %s", url)

            if method.upper() == "POST":
                response = requests.post(
                    url, json=json_data, headers=headers, timeout=30
                )
            else:
                response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if retries > 0:
                self.logger.warning(
                    "Google Maps API request failed: %s, retrying...", e
                )
                return self._make_google_maps_request(
                    url, params, json_data, headers, method, retries - 1
                )
            else:
                self.logger.error("Google Maps API request failed: %s", e)
                return None

    def _load_road_distance_cache(self) -> None:
        """
        Load road distance cache from CSV file.

        The cache stores road distances and durations between coordinate pairs
        to avoid redundant API calls.
        """
        cache_file = DATA_PATH + ROAD_DISTANCE_CACHE_FILENAME
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                for _, row in df.iterrows():
                    cache_key = f"{row['origin']}|{row['destination']}"
                    self.road_distance_cache[cache_key] = {
                        "distance_km": row["distance_km"],
                        "duration_seconds": row["duration_seconds"],
                    }
                self.logger.info(
                    "Loaded %d cached road distances", len(self.road_distance_cache)
                )
            except (
                FileNotFoundError,
                pd.errors.EmptyDataError,
                KeyError,
                ValueError,
            ) as e:
                self.logger.warning("Failed to load road distance cache: %s", e)
                self.road_distance_cache = {}
        else:
            self.logger.info("No road distance cache found, starting fresh")
            self.road_distance_cache = {}

    def _save_road_distance_cache(self) -> None:
        """
        Save road distance cache to CSV file.

        Saves the current cache to disk for future use.
        """
        if not self.road_distance_cache:
            return

        cache_file = DATA_PATH + ROAD_DISTANCE_CACHE_FILENAME
        try:
            data = []
            for cache_key, values in self.road_distance_cache.items():
                origin, destination = cache_key.split("|")
                data.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "distance_km": values["distance_km"],
                        "duration_seconds": values["duration_seconds"],
                    }
                )

            df = pd.DataFrame(data)
            df.to_csv(cache_file, index=False)
            self.logger.info(
                "Saved %d road distances to cache", len(self.road_distance_cache)
            )
        except (OSError, pd.errors.EmptyDataError, ValueError) as e:
            self.logger.error("Failed to save road distance cache: %s", e)

    def _get_cached_road_distance(
        self, origin: str, destination: str
    ) -> Optional[Tuple[float, int]]:
        """
        Get cached road distance and duration.

        Args:
            origin: Origin coordinates as "lat,lng"
            destination: Destination coordinates as "lat,lng"

        Returns:
            Tuple of (distance_km, duration_seconds) or None if not cached
        """
        # Try both directions since road distance is symmetric
        cache_key1 = f"{origin}|{destination}"
        cache_key2 = f"{destination}|{origin}"

        if cache_key1 in self.road_distance_cache:
            values = self.road_distance_cache[cache_key1]
            return values["distance_km"], values["duration_seconds"]
        elif cache_key2 in self.road_distance_cache:
            values = self.road_distance_cache[cache_key2]
            return values["distance_km"], values["duration_seconds"]

        return None

    def _cache_road_distance(
        self, origin: str, destination: str, distance_km: float, duration_seconds: int
    ) -> None:
        """
        Cache road distance and duration.

        Args:
            origin: Origin coordinates as "lat,lng"
            destination: Destination coordinates as "lat,lng"
            distance_km: Distance in kilometers
            duration_seconds: Duration in seconds
        """
        cache_key = f"{origin}|{destination}"
        self.road_distance_cache[cache_key] = {
            "distance_km": distance_km,
            "duration_seconds": duration_seconds,
        }

    def test_google_maps_request_connexion(self) -> Optional[Dict[str, Any]]:
        """
        Test the Google Maps API request.
        """
        try:
            params = {"address": "Paris", "key": self.api_key}
            response = requests.get(
                GoogleMapsUrls.GEOCODING.value, params=params, timeout=30
            )
            response_dict = response.json()
            if response_dict.get("error_message") or response.status_code != 200:
                self.logger.error(
                    "Google Maps API request failed: %s",
                    response_dict.get("error_message") or response.status_code,
                )
                return False
            else:
                return True
        except (requests.RequestException, KeyError, ValueError) as e:
            self.logger.error("Google Maps API request failed: %s", e)
            return False

    def _get_coordinates_for_place(
        self, place_name: str
    ) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a place using Google Maps Geocoding API.

        Args:
            place_name: Name of the place to geocode

        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        self.logger.info("Geocoding place: %s", place_name)

        params = {"address": place_name, "key": self.api_key}

        data = self._make_google_maps_request(
            url=GoogleMapsUrls.GEOCODING.value, params=params, method="GET"
        )

        if not data:
            self.logger.warning("No response from Geocoding API for %s", place_name)
            return None

        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            coords = (location["lat"], location["lng"])
            self.logger.info(
                "Found coordinates for %s: %.4f, %.4f", place_name, coords[0], coords[1]
            )
            return coords
        else:
            self.logger.warning(
                "Could not find coordinates for %s. Status: %s",
                place_name,
                data.get("status"),
            )
            return None

    def _get_road_distance_duration(
        self, origin: str, destination: str
    ) -> Tuple[Optional[float], Optional[int]]:
        """
        Get road distance and duration between two coordinates using the new Google Routes API.
        Uses cache to avoid redundant API calls.

        Args:
            origin: Origin coordinates as "lat,lng"
            destination: Destination coordinates as "lat,lng"

        Returns:
            Tuple of (distance_km, duration_seconds) or (None, None) if request fails
        """
        # Check cache first
        cached_result = self._get_cached_road_distance(origin, destination)
        if cached_result is not None:
            self.logger.debug(
                "Using cached road distance: %s -> %s", origin, destination
            )
            return cached_result
        self.logger.debug(
            "Making API request for road distance: %s -> %s", origin, destination
        )

        try:
            origin_lat, origin_lng = map(float, origin.split(","))
            dest_lat, dest_lng = map(float, destination.split(","))

            url = GoogleMapsUrls.DIRECTION.value
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "routes.distanceMeters,routes.duration",
            }

            body = {
                "origin": {
                    "location": {
                        "latLng": {"latitude": origin_lat, "longitude": origin_lng}
                    }
                },
                "destination": {
                    "location": {
                        "latLng": {"latitude": dest_lat, "longitude": dest_lng}
                    }
                },
                "travelMode": "DRIVE",
            }

            data = self._make_google_maps_request(
                url=url, json_data=body, headers=headers, method="POST"
            )

            if not data or "routes" not in data or len(data["routes"]) == 0:
                self.logger.warning(
                    "No routes found between %s and %s", origin, destination
                )
                return None, None

            route = data["routes"][0]
            distance_meters = route["distanceMeters"]
            duration_seconds = int(
                float(route["duration"].replace("s", ""))
            )  # "3600s" → 3600
            distance_km = distance_meters / 1000

            # Cache result
            self._cache_road_distance(
                origin, destination, distance_km, duration_seconds
            )
            self._save_road_distance_cache()

            return distance_km, duration_seconds

        except Exception as e:
            self.logger.error("Failed to fetch route distance: %s", e)
            return None, None

    def calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate the great circle distance between two points in kilometers."""
        R = 6371.0  # Earth's radius in kilometers

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        lat1 = radians(lat1)
        lat2 = radians(lat2)

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))  # Fixed the haversine formula

        return R * c

    def _load_stadium_data(self) -> None:
        """
        Load stadium location data from CSV file.

        Raises:
            FileNotFoundError: If stadium data file is not found
        """
        if not os.path.exists(DATA_PATH + LOCALISATION_STADE_FILENAME):
            self.logger.info("⚠️ Stadium data file not found, starting geocoding...")
            self.get_coordinates_stadiums()
        try:
            self.stadium_df = pd.read_csv(
                DATA_PATH + LOCALISATION_STADE_FILENAME, index_col=0
            ).reset_index(drop=True)

        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Stadium data file not found: {DATA_PATH + LOCALISATION_STADE_FILENAME}"
            ) from exc
        except Exception as e:
            raise RuntimeError(f"Error loading stadium data: {e}") from e

    def get_coordinates_stadiums(self) -> None:
        """
        Get latitude and longitude coordinates for all stadiums.

        Reads stadium names from the CSV file and uses Google Maps Geocoding API
        to get their coordinates. Saves the results to a CSV file.

        Raises:
            Exception: If API request fails or stadium not found
        """
        self.logger.info("Starting stadium coordinates retrieval...")
        stadium_data = pd.read_csv(DATA_PATH + NAME_STADE_FILENAME)

        latitude_list = []
        longitude_list = []
        total_stadiums = len(stadium_data["Stadium"])

        self.logger.info("Geocoding stadiums...")
        for stadium_name in stadium_data["Stadium"]:
            coordinates = self._get_coordinates_for_place(stadium_name)
            if coordinates:
                latitude_list.append(coordinates[0])
                longitude_list.append(coordinates[1])
            else:
                latitude_list.append(None)
                longitude_list.append(None)

        stadium_data["latitude"] = latitude_list
        stadium_data["longitude"] = longitude_list
        stadium_data.to_csv(DATA_PATH + LOCALISATION_STADE_FILENAME)

        successful_geocodes = sum(1 for lat in latitude_list if lat is not None)
        self.logger.info(
            "Stadium coordinates saved! %d/%d stadiums geocoded successfully",
            successful_geocodes,
            total_stadiums,
        )

    def _format_coordinates(self, lat: float, lon: float) -> str:
        """Format latitude and longitude into coordinate string."""
        return f"{lat},{lon}"

    def _create_route_name(self, departure: str, arrival: str) -> str:
        """Create standardized route name format."""
        return f"{departure};-{arrival}"

    def _parse_route_name(self, route_name: str) -> Tuple[str, str]:
        """Parse route name to extract departure and arrival."""
        departure, arrival = route_name.rsplit(";-", 1)
        return departure, arrival

    def _save_route_data(self, routes: List[RouteData], filename: str) -> None:
        """
        Save route data to CSV file in standardized format.

        Args:
            routes: List of RouteData objects
            filename: Output filename
        """
        self.logger.info("Saving %d routes to %s...", len(routes), filename)

        data = {
            "departure": [route.departure for route in routes],
            "arrival": [route.arrival for route in routes],
            "travel_time_seconds": [route.travel_time_seconds for route in routes],
            "distance_km": [route.distance_km for route in routes],
            "emissions_kg_co2": [route.emissions_kg_co2 for route in routes],
            "transport_type": [route.transport_type for route in routes],
        }

        # Add route-specific details by directly saving the entire route_details dict for each route
        data["route_details"] = [route.route_details for route in routes]

        df = pd.DataFrame(data)
        df.to_csv(DATA_PATH + filename, index=False)

        # Create a nice summary table
        table = Table(title=f"Route Data Summary - {filename}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Routes", str(len(routes)))
        table.add_row("Transport Type", routes[0].transport_type if routes else "N/A")
        table.add_row(
            "Total Distance (km)", f"{sum(route.distance_km for route in routes):.2f}"
        )
        table.add_row(
            "Total Emissions (kg CO2)",
            f"{sum(route.emissions_kg_co2 for route in routes):.2f}",
        )
        table.add_row("File Location", DATA_PATH + filename)

        self.console.print(table)
        self.logger.info("Route data successfully saved to %s", filename)

    @abstractmethod
    def calculate_route(
        self,
        departure: str,
        arrival: str,
        departure_coords: Tuple[float, float],
        arrival_coords: Tuple[float, float],
    ) -> Optional[RouteData]:
        """
        Calculate route between two points. Must be implemented by subclasses.

        Args:
            departure: Departure location name
            arrival: Arrival location name
            departure_coords: Departure coordinates (lat, lng)
            arrival_coords: Arrival coordinates (lat, lng)

        Returns:
            RouteData object or None if calculation fails
        """

    def process_all_routes(self, output_filename: str | None = None) -> List[RouteData]:
        """
        Process all possible routes between stadiums.

        Returns:
            List of RouteData objects for all stadium pairs
        """
        self.logger.info("Starting route processing...")
        routes = []

        # Create a set to keep track of already computed stadium pairs
        computed_pairs = set()

        # Try to load already saved routes to avoid recomputation
        if output_filename is not None:
            try:
                existing_df = pd.read_csv(DATA_PATH + output_filename).reset_index(
                    drop=True
                )
                for _, row in existing_df.iterrows():
                    dep = row["departure"]
                    arr = row["arrival"]
                    # Use frozenset to treat route between A <-> B as interchangeable
                    computed_pairs.add(frozenset((dep, arr)))
                    # Initialize routes list from existing file
                    route = RouteData(
                        departure=row["departure"],
                        arrival=row["arrival"],
                        travel_time_seconds=int(row["travel_time_seconds"]),
                        distance_km=float(row["distance_km"]),
                        emissions_kg_co2=float(row["emissions_kg_co2"]),
                        transport_type=row["transport_type"],
                        route_details=row["route_details"],
                    )
                    routes.append(route)

            except (FileNotFoundError, pd.errors.EmptyDataError, KeyError):
                self.logger.warning("No existing routes file found, starting fresh")

        # Calculate total number of route pairs
        total_teams = len(self.stadium_df)
        total_routes = total_teams * (total_teams - 1) // 2

        self.logger.info(
            "Processing %d unique routes between %d teams", total_routes, total_teams
        )

        for i, stadium_row in self.stadium_df.iterrows():
            print(i)
            departure = stadium_row["Team"]  # Team name
            departure_coords = (
                stadium_row["latitude"],
                stadium_row["longitude"],
            )  # lat, lng

            # Only iterate through teams that come after the current team to avoid duplicates
            for _, stadium_row2 in self.stadium_df.iloc[i + 1 :].iterrows():
                arrival = stadium_row2["Team"]  # Team name
                arrival_coords = (
                    stadium_row2["latitude"],
                    stadium_row2["longitude"],
                )  # lat, lng

                pair_key = frozenset((departure, arrival))
                if pair_key in computed_pairs:
                    self.logger.debug(
                        "Skipping already computed route: %s -> %s", departure, arrival
                    )
                    continue

                self.logger.debug("Calculating route: %s -> %s", departure, arrival)
                route = self.calculate_route(
                    departure, arrival, departure_coords, arrival_coords
                )
                if route:
                    routes.append(route)
                    computed_pairs.add(pair_key)
                    if output_filename:
                        self._save_route_data(routes, output_filename)
        self.logger.info(
            "Route processing complete! %d routes calculated successfully", len(routes)
        )
        return routes

    def run_complete_analysis(self, output_filename: str) -> List[RouteData]:
        """
        Run the complete analysis pipeline.

        Args:
            output_filename: Name of the output CSV file

        Returns:
            List of RouteData objects
        """
        self.logger.info(
            "Starting complete %s analysis...", str(self.__class__.__name__)
        )

        routes = self.process_all_routes(output_filename)

        if routes:
            self._save_route_data(routes, output_filename)

        else:
            self.logger.warning("No routes were processed.")

        # Save road distance cache for future use
        self._save_road_distance_cache()

        return routes
