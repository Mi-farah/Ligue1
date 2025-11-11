# Route Comparison App

A Streamlit web application to compare car, train, and plane routes between Ligue 1 teams to verify emission calculations.

## Features

- **Single Team View**: See all routes from/to a selected team with comparison metrics
- **Two Team Comparison**: Compare routes between two specific teams
- **Interactive Map Visualization**: Visualize routes on an interactive map with:
  - 🚗 **Car routes**: Blue lines connecting stadiums
  - 🚂 **Train routes**: Green dashed lines with station markers
  - ✈️ **Plane routes**: Red lines for flights, orange dashed lines for airport transfers, with airport markers
- **Detailed Route Information**: View step-by-step route details including:
  - Distances for each segment
  - Travel times
  - CO₂ emissions breakdown
  - For trains: train segments and car segments to/from stations
  - For planes: flight details, airport transfers, and autocar routes
  - For cars: direct route information

## Installation

1. Install dependencies (if not already done):
   ```bash
   uv sync
   ```

## Running the App

1. Start the Streamlit app:
   ```bash
   uv run streamlit run route_comparison_app.py
   ```

2. The app will open in your default web browser at `http://localhost:8501`

## Usage

### Single Team Mode
1. Select "Single Team (all routes)" from the sidebar
2. Choose a team from the dropdown
3. View a comparison table of all routes from/to that team
4. Select a specific route to see detailed information

### Two Team Comparison Mode
1. Select "Between Two Teams" from the sidebar
2. Choose departure and arrival teams
3. View side-by-side comparison of car, train, and plane routes
4. **See the routes on an interactive map** showing all three transport types with different colors and step-by-step markers
5. Click on the tabs to see detailed route information for each transport type

### Map Features
- **Car routes**: Shown in blue, direct connection between stadiums
- **Train routes**: Shown in green with dashed lines, includes intermediate train stations
- **Plane routes**: 
  - Red solid lines for flight segments
  - Orange dashed lines for autocar transfers to/from airports
  - Airport markers with detailed information

## Data Sources

The app reads from three CSV files:
- `backend/data/calculated_travels/car_emissions.csv`
- `backend/data/calculated_travels/train_emissions.csv`
- `backend/data/calculated_travels/flight_emissions.csv`

## Verification Tips

When verifying calculations, check:
- **Distance consistency**: Are distances reasonable for the route?
- **Time calculations**: Do travel times match the distances and transport types?
- **Emission factors**: Are CO₂ emissions calculated correctly based on distances?
- **Route details**: For trains, verify station segments. For planes, check airport transfers.
- **Bidirectional routes**: The app handles routes in both directions automatically

