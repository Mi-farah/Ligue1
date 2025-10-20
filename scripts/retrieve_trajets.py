import os

from dotenv import load_dotenv

from backend.services.car_service import CarTrajetService
from backend.services.plane_service import PlaneTrajetService
from backend.services.train_service import TrainTrajetService

load_dotenv()
api_key = os.getenv("GOOGLE_MAPS_API_KEY")
sncf_api_key = os.getenv("SNCF_API_KEY")


def main():
    # Initialize services
    train_service = TrainTrajetService(api_key, sncf_api_key)
    plane_service = PlaneTrajetService(api_key)
    car_service = CarTrajetService(api_key)

    # Run the complete analysis for each transport mode
    train_service.run_complete_analysis()
    plane_service.run_complete_analysis()
    car_service.run_complete_analysis()


if __name__ == "__main__":
    main()
