from enum import Enum

DATA_PATH = "./backend/data/calculated_travels/"
NAME_STADE_FILENAME = 'name-stade.csv'
AIRPORT_CACHE_FILENAME = "airport_cache.csv"
FLIGHT_EMISSIONS_FILENAME = "flight_emissions.csv"
LOCALISATION_STADE_FILENAME = 'localisation_stade.csv'
CAR_EMISSIONS_FILENAME = "car_emissions.csv"
TRAIN_EMISSIONS_FILENAME = "train_emissions.csv"

class TravelMode(Enum):
    """Travel modes for Google Maps API."""
    CAR = "CAR"
    TRAIN = "TRAIN"
    BUS = "BUS"
    PLANE = "PLANE"


class PlaceType(Enum):
    """Place types for Google Maps Places API."""
    AIRPORT = "airport"
    TRAIN_STATION = "train_station"
    BUS_STATION = "bus_station"
    SUBWAY_STATION = "subway_station"

class GoogleMapsUrls(Enum):
    """Dataclass containing all Google Maps API endpoints and configurations."""
    
    # Specific endpoints
    GEOCODING: str = "https://maps.googleapis.com/maps/api/geocode/json"
    NEARBY_PLACE: str = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    DIRECTION: str = "https://maps.googleapis.com/maps/api/directions/json"


## CO2 emissions calculations variables

# General
NUMBER_OF_PASSENGERS = 50 # Number of passengers (team + staff)

# Car
AUTO_CAR_EMISSION_FACTOR = 0.030  # kgCO2/passenger/km (https://bigmedia.bpifrance.fr/nos-dossiers/empreinte-carbone-des-trajets-en-train-calcul-et-decarbonation)

# Train
TRAIN_EMISSION_FACTOR = 0.0091375  # kgCO2/passenger/km (https://bigmedia.bpifrance.fr/nos-dossiers/empreinte-carbone-des-trajets-en-train-calcul-et-decarbonation)
# mean of the following values:
# Intercité = 5,3 gCO2/km ;
# RER = 4,75 gCO2/km ;
# TER = 24,8 gCO2/km ;
# TGV = 1,7 gCO2/km.

"""
- utiliser les trajets de Lou
- faire les trajets à vide de bus (fixé)
- faire les trajets en avion depuis la liste des aéroports
- faire les trajets en train en gare fixé
"""