import pandas as pd
import os
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from backend.global_variables import DATA_PATH, LOCALISATION_STADE_FILENAME, NAME_STADE_FILENAME, GoogleMapsUrls
from math import radians, sin, cos, sqrt, asin
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
import logging


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
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True)]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _make_google_maps_request(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make a request to Google Maps API with error handling.
        
        Args:
            url: API endpoint URL
            params: Request parameters
            
        Returns:
            API response data or None if request fails
        """
        try:
            self.logger.debug("Making Google Maps API request to: %s", url)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            if response.status_code == 200:
                self.logger.debug("Google Maps API request successful")
                return response.json()
            else:
                self.logger.error("Google Maps API request failed: %s", response.status_code)
                return None
        except requests.RequestException as e:
            self.logger.error("Google Maps API request failed: %s", e)
            return None
    
    def test_google_maps_request_connexion(self) -> Optional[Dict[str, Any]]:
        """
        Test the Google Maps API request.
        """
        try:
            params = {
                "address": "Paris",
                "key": self.api_key
            }
            response = requests.get(GoogleMapsUrls.GEOCODING.value, params=params, timeout=30)
            print(response.json())
            if response.status_code == 200:
                self.logger.info("Google Maps API request successful")
                return True
            else:
                self.logger.error("Google Maps API request failed: %s, %s", response.status_code, response.text)
                return False
        except requests.RequestException as e:
            self.logger.error("Google Maps API request failed: %s", e)
            return False
    
    def _get_coordinates_for_place(self, place_name: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a place using Google Maps Geocoding API.
        
        Args:
            place_name: Name of the place to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        self.logger.info("🔍 Geocoding place: %s", place_name)
        params = {
            "address": place_name,
            "key": self.api_key
        }
        
        data = self._make_google_maps_request(GoogleMapsUrls.GEOCODING.value, params)
        if data and data.get('status') == 'OK':
            location = data['results'][0]['geometry']['location']
            coords = (location['lat'], location['lng'])
            self.logger.info("✅ Found coordinates for %s: %.4f, %.4f", place_name, coords[0], coords[1])
            return coords
        else:
            self.logger.warning("❌ Could not find coordinates for %s", place_name)
            return None
    
    def _get_road_distance_duration(self, origin: str, destination: str) -> Tuple[Optional[float], Optional[int]]:
        """
        Get road distance and duration between two coordinates.
        
        Args:
            origin: Origin coordinates as "lat,lng"
            destination: Destination coordinates as "lat,lng"
            
        Returns:
            Tuple of (distance_km, duration_seconds) or (None, None) if request fails
        """
        params = {
            "origin": origin,
            "destination": destination,
            "mode": "driving",
            "alternatives": "false",
            "key": self.api_key
        }
        
        data = self._make_google_maps_request(GoogleMapsUrls.DIRECTION.value, params)
        if data and data.get("status") == "OK" and data.get("routes"):
            leg = data["routes"][0]["legs"][0]
            distance_meters = leg["distance"]["value"]
            duration_seconds = leg["duration"]["value"]
            return distance_meters / 1000, duration_seconds  # Convert to km
        return None, None
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points in kilometers."""
        R = 6371.0  # Earth's radius in kilometers

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        lat1 = radians(lat1)
        lat2 = radians(lat2)

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a))  # Fixed the haversine formula

        return R * c
    
    def _load_stadium_data(self) -> pd.DataFrame:
        """
        Load stadium location data from CSV file.
        
        Returns:
            DataFrame containing stadium data
            
        Raises:
            FileNotFoundError: If stadium data file is not found
        """
        if not os.path.exists(DATA_PATH + LOCALISATION_STADE_FILENAME):
            self.get_coordinates_stadiums()
        try:
            return pd.read_csv(DATA_PATH + LOCALISATION_STADE_FILENAME, index_col=0)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Stadium data file not found: {DATA_PATH + LOCALISATION_STADE_FILENAME}") from exc
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
        self.logger.info("🏟️ Starting stadium coordinates retrieval...")
        stadium_data = pd.read_csv(DATA_PATH + NAME_STADE_FILENAME)

        latitude_list = []
        longitude_list = []
        total_stadiums = len(stadium_data["Stadium"])

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Geocoding stadiums...", total=total_stadiums)
            
            for stadium_name in stadium_data["Stadium"]:
                coordinates = self._get_coordinates_for_place(stadium_name)
                if coordinates:
                    latitude_list.append(coordinates[0])
                    longitude_list.append(coordinates[1])
                else:
                    latitude_list.append(None)
                    longitude_list.append(None)
                
                progress.advance(task)

        stadium_data["latitude"] = latitude_list
        stadium_data["longitude"] = longitude_list
        stadium_data.to_csv(DATA_PATH + LOCALISATION_STADE_FILENAME)
        
        successful_geocodes = sum(1 for lat in latitude_list if lat is not None)
        self.logger.info("✅ Stadium coordinates saved! %d/%d stadiums geocoded successfully", successful_geocodes, total_stadiums)

    def _format_coordinates(self, lat: float, lon: float) -> str:
        """Format latitude and longitude into coordinate string."""
        return f"{lat},{lon}"
    
    def _create_route_name(self, departure: str, arrival: str) -> str:
        """Create standardized route name format."""
        return f"{departure};-{arrival}"
    
    def _parse_route_name(self, route_name: str) -> Tuple[str, str]:
        """Parse route name to extract departure and arrival."""
        departure, arrival = route_name.rsplit(';-', 1)
        return departure, arrival
    
    def _save_route_data(self, routes: List[RouteData], filename: str) -> None:
        """
        Save route data to CSV file in standardized format.
        
        Args:
            routes: List of RouteData objects
            filename: Output filename
        """
        self.logger.info("💾 Saving %d routes to %s...", len(routes), filename)
        
        data = {
            "departure": [route.departure for route in routes],
            "arrival": [route.arrival for route in routes],
            "travel_time_seconds": [route.travel_time_seconds for route in routes],
            "distance_km": [route.distance_km for route in routes],
            "emissions_kg_co2": [route.emissions_kg_co2 for route in routes],
            "transport_type": [route.transport_type for route in routes]
        }
        
        # Add route-specific details if available
        if routes and routes[0].route_details:
            for key in routes[0].route_details.keys():
                data[key] = [route.route_details.get(key) for route in routes]
        
        df = pd.DataFrame(data)
        df.to_csv(DATA_PATH + filename, index=False)
        
        # Create a nice summary table
        table = Table(title=f"Route Data Summary - {filename}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Routes", str(len(routes)))
        table.add_row("Transport Type", routes[0].transport_type if routes else "N/A")
        table.add_row("Total Distance (km)", f"{sum(route.distance_km for route in routes):.2f}")
        table.add_row("Total Emissions (kg CO2)", f"{sum(route.emissions_kg_co2 for route in routes):.2f}")
        table.add_row("File Location", DATA_PATH + filename)
        
        self.console.print(table)
        self.logger.info("✅ Route data successfully saved to %s", filename)
    
    @abstractmethod
    def calculate_route(self, departure: str, arrival: str, departure_coords: Tuple[float, float], 
                       arrival_coords: Tuple[float, float]) -> Optional[RouteData]:
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
    
    
    def process_all_routes(self) -> List[RouteData]:
        """
        Process all possible routes between stadiums.

        
        Returns:
            List of RouteData objects for all stadium pairs
        """
        self.logger.info("🚀 Starting route processing...")
        stadium_df = self._load_stadium_data()
        routes = []
        
        # Calculate total number of route pairs
        total_teams = len(stadium_df)
        total_routes = total_teams * (total_teams - 1) // 2
        
        self.logger.info("📊 Processing %d unique routes between %d teams", total_routes, total_teams)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Calculating routes...", total=total_routes)
            
            for i, stadium_row in stadium_df.iterrows():
                departure = stadium_row["Team"]  # Team name
                departure_coords = (stadium_row["latitude"], stadium_row["longitude"])  # lat, lng
                
                # Only iterate through teams that come after the current team to avoid duplicates
                for _, stadium_row2 in stadium_df.iloc[i+1:].iterrows():
                    arrival = stadium_row2["Team"]  # Team name
                    arrival_coords = (stadium_row2["latitude"], stadium_row2["longitude"])  # lat, lng
                    
                    route = self.calculate_route(departure, arrival, departure_coords, arrival_coords)
                    if route:
                        routes.append(route)
                    
                    progress.advance(task)
        
        self.logger.info("✅ Route processing complete! %d routes calculated successfully", len(routes))
        return routes


    def run_complete_analysis(self, output_filename: str) -> List[RouteData]:
        """
        Run the complete analysis pipeline.
        
        Args:
            output_filename: Name of the output CSV file
            
        Returns:
            List of RouteData objects
        """
        transport_type = self.__class__.__name__.replace("Service", "").lower()
        
        # Create a nice header panel
        header_panel = Panel(
            f"[bold blue]{self.__class__.__name__}[/bold blue]\n"
            f"[green]Transport Type:[/green] {transport_type.title()}\n"
            f"[green]Output File:[/green] {output_filename}",
            title="🚀 Transport Analysis Started",
            border_style="blue"
        )
        self.console.print(header_panel)
        
        self.logger.info("Starting complete %s analysis...", self.__class__.__name__)
        
        routes = self.process_all_routes()
        
        if routes:
            self._save_route_data(routes, output_filename)
            
        else:
            error_panel = Panel(
                "[bold red]❌ No routes were processed![/bold red]\n"
                "Please check your configuration and try again.",
                title="⚠️ Analysis Failed",
                border_style="red"
            )
            self.console.print(error_panel)
            self.logger.warning("No routes were processed.")
        
        return routes