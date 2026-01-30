# Ligue1 team travel CO2 Emissions

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg) ![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg) ![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-brightgreen)

Estimate CO₂ emissions for Ligue 1 team travel by rail, road, and air. The project combines routing (Google Maps API), emission factors, and reproducible scripts to generate transparent calculations and shareable outputs.

## Repository structure

- **backend/services/**: Transport service classes for train, plane, and car calculations
- **backend/data/**: Input/output CSVs, including computed travel emissions
- **scripts/**: Entry points such as `retrieve_trajets` for end-to-end recomputation, and `calculate_emissions` to compute the final emissions.

## Requirements

- Python 3.8+ (uv recommended for environment management)
- Google Maps API key (`GOOGLE_MAPS_API_KEY` in `.env`)

## Setup

1. Install uv (recommended):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Windows PowerShell:
   # powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. Create and populate `.env` at the repo root:
   ```
   GOOGLE_MAPS_API_KEY=your_api_key_here
   ```
3. Install dependencies and create the virtual environment:
   ```bash
   uv sync
   ```

## Usage

- Recompute all routes and emissions (train, plane, car):
  ```bash
  uv run python -m scripts.retrieve_trajets
  ```
- Outputs are written to `backend/data/calculated_travels/`, including:
  - `train_emissions.csv`
  - `flight_emissions.csv`
  - `car_emissions.csv`
  - aggregated tables such as `total_emissions.csv`

- Compute the emissions table with:
  ```bash
  uv run python -m scripts.calculate_emissions
  ```

## Citation & Attribution (Required)

This project and its data are protected under the French Intellectual Property Code (Article L121-1). If you use this software, the computed emissions data, or the methodology in your reporting, **attribution is legally required.**

Please cite the authors as follows:

> Farah, M., Muhieddine, U., & Stührenberg, L. (2026). Ligue1 Emissions. Source: https://github.com/Mi-farah/Ligue1

For academic or technical use, please refer to the `CITATION.cff` file.

## License

This project is licensed under the MIT License. See `LICENSE` for details. Any reproduction, representation, or public use of this work without proper attribution constitutes an infringement of the authors' moral rights under Article L121-1 of the French Intellectual Property Code.
