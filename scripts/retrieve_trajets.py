import os
from dotenv import load_dotenv

from backend.services.train_service import TrainTrajetService
from backend.services.plane_service import PlaneTrajetService
from backend.services.car_service import CarTrajetService
from backend.global_variables import TRAIN_EMISSIONS_FILENAME, FLIGHT_EMISSIONS_FILENAME, CAR_EMISSIONS_FILENAME

load_dotenv()
api_key = os.getenv("GOOGLE_MAPS_API_KEY")
sncf_api_key = os.getenv("SNCF_API_KEY")

def main():
    # Initialize services
    train_service = TrainTrajetService(api_key, sncf_api_key)
    plane_service = PlaneTrajetService(api_key)
    car_service = CarTrajetService(api_key)

    # if train_service.test_google_maps_request_connexion():
    #     train_service.run_complete_analysis()

    # if plane_service.test_google_maps_request_connexion():
    #     plane_service.run_complete_analysis()

    if car_service.test_google_maps_request_connexion():
        car_service.run_complete_analysis()

if __name__ == "__main__":
    main()
