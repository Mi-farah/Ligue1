"""
Route Comparison App for Ligue 1 Emissions
Compare car, train, and plane routes between teams to verify calculations
"""

import ast
import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# Set page config
st.set_page_config(page_title="Ligue 1 Route Comparison", page_icon="⚽", layout="wide")

# Data paths
DATA_DIR = Path(__file__).parent / "backend" / "data" / "calculated_travels"
CAR_CSV = DATA_DIR / "car_emissions.csv"
TRAIN_CSV = DATA_DIR / "train_emissions.csv"
FLIGHT_CSV = DATA_DIR / "flight_emissions.csv"
STADIUM_CSV = DATA_DIR / "localisation_stade.csv"
GARE_CSV = DATA_DIR / "gare_positions.csv"
GARE_CACHE_CSV = DATA_DIR / "general_gare_position_cache.csv"


@st.cache_data
def load_data():
    """Load all three CSV files"""
    car_df = pd.read_csv(CAR_CSV)
    train_df = pd.read_csv(TRAIN_CSV)
    flight_df = pd.read_csv(FLIGHT_CSV)
    return car_df, train_df, flight_df


@st.cache_data
def load_stadium_data():
    """Load stadium coordinates"""
    try:
        stadium_df = pd.read_csv(STADIUM_CSV, index_col=0)
        return stadium_df
    except FileNotFoundError:
        return None


@st.cache_data
def load_gare_data():
    """Load gare (train station) coordinates"""
    try:
        gare_df = pd.read_csv(GARE_CSV)
        return gare_df
    except FileNotFoundError:
        return None


@st.cache_data
def load_gare_cache_data():
    """Load general gare position cache with all stations involved in train routes"""
    try:
        gare_cache_df = pd.read_csv(GARE_CACHE_CSV)
        return gare_cache_df
    except FileNotFoundError:
        return None


def get_gare_coords(_gare_df, gare_name, gare_cache_df=None):
    """Get gare coordinates by matching gare name, using cache first"""
    if not gare_name:
        return None

    # First try the general cache (has all stations)
    if gare_cache_df is not None:
        matches = gare_cache_df[gare_cache_df["base_name"] == gare_name]

        if not matches.empty:
            lat = matches.iloc[0].get("latitude")
            lon = matches.iloc[0].get("longitude")
            if pd.notna(lat) and pd.notna(lon):
                return (float(lat), float(lon))
    return None


def get_stadium_coords(stadium_df, team_name):
    """Get stadium coordinates for a team"""
    if stadium_df is None:
        return None
    # Try to match by Team column or Location
    team_row = stadium_df[stadium_df["Team"] == team_name]
    if team_row.empty:
        team_row = stadium_df[stadium_df["Location"] == team_name]
    if not team_row.empty:
        lat = team_row.iloc[0].get("latitude")
        lon = team_row.iloc[0].get("longitude")
        if pd.notna(lat) and pd.notna(lon):
            return (float(lat), float(lon))
    return None


def create_route_map(
    car_route,
    train_route,
    plane_route,
    departure,
    arrival,
    stadium_df,
    gare_df,
    gare_cache_df,
):
    """Create a folium map showing all three route types"""
    # Get center point - use stadium coordinates or first available route point
    center_lat, center_lon = 46.5, 2.5  # Default center of France

    # Try to get stadium coordinates
    dep_coords = get_stadium_coords(stadium_df, departure)
    arr_coords = get_stadium_coords(stadium_df, arrival)

    if dep_coords and arr_coords:
        center_lat = (dep_coords[0] + arr_coords[0]) / 2
        center_lon = (dep_coords[1] + arr_coords[1]) / 2
    elif dep_coords:
        center_lat, center_lon = dep_coords
    elif arr_coords:
        center_lat, center_lon = arr_coords

    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    # Add legend
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; z-index:9999; font-size:13px;
                border:2px solid grey; padding: 12px; border-radius: 5px;
                color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
    <p style="color: black; margin: 0 0 5px 0;"><b>📍 Route Types</b></p>
    <hr style="margin: 5px 0; border-color: #ccc;">
    <p style="color: black; margin: 3px 0;"><b>🚗 Car:</b> <span style="color:blue; font-weight: bold;">━━━</span> Blue</p>
    <p style="color: black; margin: 3px 0;"><b>🚂 Train:</b> <span style="color:green; font-weight: bold;">━━━</span> Plain, <span style="color:green; font-weight: bold;">━ ━ ━</span> Dashed (car)</p>
    <p style="color: black; margin: 3px 0;"><b>✈️ Plane:</b> <span style="color:red; font-weight: bold;">━━━</span> Plain (flight), <span style="color:red; font-weight: bold;">━ ━ ━</span> Dashed (car)</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Plot Car route
    if car_route is not None:
        car_details = parse_route_details(car_route["route_details"])
        plot_car_route(
            m, car_route, car_details, departure, arrival, dep_coords, arr_coords
        )

    # Plot Train route
    if train_route is not None:
        train_details = parse_route_details(train_route["route_details"])
        plot_train_route(
            m,
            train_route,
            train_details,
            departure,
            arrival,
            dep_coords,
            arr_coords,
            gare_df,
            gare_cache_df,
        )

    # Plot Plane route
    if plane_route is not None:
        plane_details = parse_route_details(plane_route["route_details"])
        plot_plane_route(
            m, plane_route, plane_details, departure, arrival, dep_coords, arr_coords
        )

    # Add departure and arrival markers (always visible)
    if dep_coords:
        folium.CircleMarker(
            dep_coords,
            radius=8,
            popup=f"<b>Departure: {departure}</b><br>Stadium",
            color="black",
            fillColor="white",
            fillOpacity=1.0,
            weight=3,
        ).add_to(m)

    if arr_coords:
        folium.CircleMarker(
            arr_coords,
            radius=8,
            popup=f"<b>Arrival: {arrival}</b><br>Stadium",
            color="black",
            fillColor="white",
            fillOpacity=1.0,
            weight=3,
        ).add_to(m)

    return m


def plot_car_route(
    map_obj, route, _details, departure, arrival, dep_coords, arr_coords
):
    """Plot car route on map using stadium coordinates from localisation_stade.csv"""
    # Use stadium coordinates from localisation_stade.csv
    if not dep_coords or not arr_coords:
        return  # Need both coordinates to plot

    points = [dep_coords, arr_coords]

    # Draw line between stadiums (blue plain)
    folium.PolyLine(
        points,
        color="blue",
        weight=4,
        opacity=0.7,
        popup=f"<b>Car Route</b><br>{departure} → {arrival}<br>Distance: {route['distance_km']:.2f} km<br>Time: {format_time(route['travel_time_seconds'])}<br>CO₂: {route['emissions_kg_co2']:.2f} kg",
    ).add_to(map_obj)

    # Simple node markers for stadiums
    folium.CircleMarker(
        dep_coords,
        radius=6,
        popup=f"<b>{departure}</b><br>Stadium",
        color="blue",
        fillColor="blue",
        fillOpacity=0.8,
        weight=2,
    ).add_to(map_obj)

    folium.CircleMarker(
        arr_coords,
        radius=6,
        popup=f"<b>{arrival}</b><br>Stadium",
        color="blue",
        fillColor="blue",
        fillOpacity=0.8,
        weight=2,
    ).add_to(map_obj)


def plot_train_route(
    map_obj,
    _route,
    details,
    departure,
    arrival,
    dep_coords,
    arr_coords,
    gare_df,
    gare_cache_df,
):
    """Plot train route on map with real gare positions from general_gare_position_cache.csv"""
    if not details:
        return

    train_segments = details.get("train_route_details", [])
    if not train_segments:
        return

    processed_gares = {}  # Track gares we've already marked: {gare_name: coords}
    station_sequence = []  # Track stations in order of appearance

    # Plot car segments to/from stations (green dashed)
    car_segments = details.get("car_route_details", {}).get("segments", [])
    for car_seg in car_segments:
        from_name = car_seg.get("from", "")
        to_name = car_seg.get("to", "")

        # Check if "from" is a stadium
        from_coords = None
        if from_name and "Stade" in from_name:
            # It's a stadium name, try to get stadium coords
            if from_name.startswith("Stade"):
                # Try to match by team name
                if dep_coords and departure in from_name:
                    from_coords = dep_coords
                elif arr_coords and arrival in from_name:
                    from_coords = arr_coords
        else:
            # It's a gare name
            from_coords = get_gare_coords(gare_df, from_name, gare_cache_df)

        # Check if "to" is a gare (most likely for car segments)
        to_coords = get_gare_coords(gare_df, to_name, gare_cache_df)

        # Draw car segment if we have both coordinates (green dashed)
        if from_coords and to_coords:
            folium.PolyLine(
                [from_coords, to_coords],
                color="green",
                weight=3,
                opacity=0.6,
                dashArray="10, 5",
                popup=f"<b>Car to/from Station</b><br>{from_name} → {to_name}<br>Distance: {car_seg.get('distance_km', 0):.2f} km",
            ).add_to(map_obj)

    # Process each train segment (green plain)
    for segment in train_segments:
        segment_type = segment.get("type", "")

        # Skip transfer segments visually (they're within the same station)
        if segment_type == "transfer":
            continue

        from_gare_name = segment.get("from", "")
        to_gare_name = segment.get("to", "")

        # Get coordinates for both gares from cache
        from_coords = get_gare_coords(gare_df, from_gare_name, gare_cache_df)
        to_coords = get_gare_coords(gare_df, to_gare_name, gare_cache_df)

        if from_coords and to_coords:
            # Track gares in correct sequence order
            if from_gare_name not in processed_gares:
                processed_gares[from_gare_name] = from_coords
                if from_gare_name not in station_sequence:
                    station_sequence.append(from_gare_name)

            if to_gare_name not in processed_gares:
                processed_gares[to_gare_name] = to_coords
                if to_gare_name not in station_sequence:
                    station_sequence.append(to_gare_name)

            # Draw train segment line (green plain)
            distance = segment.get("distance_km", 0)
            time_s = segment.get("time_s", 0)
            co2_kg = segment.get("co2_kg", 0)

            folium.PolyLine(
                [from_coords, to_coords],
                color="green",
                weight=4,
                opacity=0.7,
                popup=(
                    f"<b>Train Segment</b><br>"
                    f"{from_gare_name} → {to_gare_name}<br>"
                    f"Distance: {distance:.2f} km<br>"
                    f"Time: {format_time(time_s)}<br>"
                    f"CO₂: {co2_kg:.4f} kg"
                ),
            ).add_to(map_obj)

    # Add simple node markers for each gare
    for gare_name in station_sequence:
        if gare_name not in processed_gares:
            continue

        gare_coords = processed_gares[gare_name]

        folium.CircleMarker(
            gare_coords,
            radius=6,
            popup=f"<b>{gare_name}</b><br>Train Station",
            color="green",
            fillColor="green",
            fillOpacity=0.8,
            weight=2,
        ).add_to(map_obj)

    # Add simple node markers for stadiums if coordinates are available
    if dep_coords:
        folium.CircleMarker(
            dep_coords,
            radius=6,
            popup=f"<b>{departure}</b><br>Stadium",
            color="green",
            fillColor="green",
            fillOpacity=0.8,
            weight=2,
        ).add_to(map_obj)

    if arr_coords:
        folium.CircleMarker(
            arr_coords,
            radius=6,
            popup=f"<b>{arrival}</b><br>Stadium",
            color="green",
            fillColor="green",
            fillOpacity=0.8,
            weight=2,
        ).add_to(map_obj)

    # Draw connection from departure stadium to first gare if we have both (green dashed)
    if dep_coords and station_sequence:
        first_gare_coords = processed_gares.get(station_sequence[0])
        if first_gare_coords:
            folium.PolyLine(
                [dep_coords, first_gare_coords],
                color="green",
                weight=3,
                opacity=0.6,
                dashArray="10, 5",
                popup="<b>Car to Station</b><br>Stadium → First Gare",
            ).add_to(map_obj)

    # Draw connection from last gare to arrival stadium if we have both (green dashed)
    if arr_coords and station_sequence:
        last_gare_coords = processed_gares.get(station_sequence[-1])
        if last_gare_coords:
            folium.PolyLine(
                [last_gare_coords, arr_coords],
                color="green",
                weight=3,
                opacity=0.6,
                dashArray="10, 5",
                popup="<b>Car from Station</b><br>Last Gare → Stadium",
            ).add_to(map_obj)


def plot_plane_route(
    map_obj, _route, details, _departure, _arrival, _dep_coords, _arr_coords
):
    """Plot plane route on map showing all 3 step types: autocar_departure, flight, autocar_arrival"""
    if not details or "travel_steps" not in details:
        return

    travel_steps = details.get("travel_steps", [])
    processed_locations = set()  # Track which locations we've already marked

    # Plot each step with distinct styling
    for step in travel_steps:
        from_coords = step.get("from_coords")
        to_coords = step.get("to_coords")
        step_type = step.get("step_type", "unknown")

        if not from_coords or not to_coords:
            continue

        from_coords_tuple = (from_coords[0], from_coords[1])
        to_coords_tuple = (to_coords[0], to_coords[1])

        # Distinct styling for each step type
        if step_type == "flight":
            # Flight segment: red solid line
            color = "red"
            weight = 5
            dash_array = None
            step_label = "Flight"
        elif step_type in ("autocar_departure", "autocar_arrival"):
            # Autocar segments: red dashed line
            color = "red"
            weight = 4
            dash_array = "10, 5"
            step_label = "Car to/from Airport"
        else:
            # Unknown step type
            color = "gray"
            weight = 3
            dash_array = "5, 5"
            step_label = "Unknown"

        # Draw line for this step
        distance = step.get("distance_km", 0)
        time = format_time(step.get("travel_time_seconds", 0))
        popup_text = (
            f"<b>{step_label}</b><br>"
            f"{step.get('from', 'N/A')} → {step.get('to', 'N/A')}<br>"
            f"Distance: {distance:.2f} km<br>"
            f"Time: {time}"
        )

        folium.PolyLine(
            [from_coords_tuple, to_coords_tuple],
            color=color,
            weight=weight,
            opacity=0.7,
            dashArray=dash_array,
            popup=popup_text,
        ).add_to(map_obj)

        # Add simple node markers for all locations
        # Mark departure location (for autocar_departure)
        if step_type == "autocar_departure":
            if from_coords_tuple not in processed_locations:
                folium.CircleMarker(
                    from_coords_tuple,
                    radius=6,
                    popup=f"<b>{step.get('from', 'N/A')}</b><br>Departure City",
                    color="red",
                    fillColor="red",
                    fillOpacity=0.8,
                    weight=2,
                ).add_to(map_obj)
                processed_locations.add(from_coords_tuple)

        # Mark airports (for flight step - both from and to)
        if step_type == "flight":
            # Origin airport
            if from_coords_tuple not in processed_locations:
                folium.CircleMarker(
                    from_coords_tuple,
                    radius=6,
                    popup=f"<b>{step.get('from', 'N/A')}</b><br>Airport",
                    color="red",
                    fillColor="red",
                    fillOpacity=0.8,
                    weight=2,
                ).add_to(map_obj)
                processed_locations.add(from_coords_tuple)

            # Destination airport
            if to_coords_tuple not in processed_locations:
                folium.CircleMarker(
                    to_coords_tuple,
                    radius=6,
                    popup=f"<b>{step.get('to', 'N/A')}</b><br>Airport",
                    color="red",
                    fillColor="red",
                    fillOpacity=0.8,
                    weight=2,
                ).add_to(map_obj)
                processed_locations.add(to_coords_tuple)

        # Mark arrival location (for autocar_arrival)
        if step_type == "autocar_arrival":
            if to_coords_tuple not in processed_locations:
                folium.CircleMarker(
                    to_coords_tuple,
                    radius=6,
                    popup=f"<b>{step.get('to', 'N/A')}</b><br>Arrival City",
                    color="red",
                    fillColor="red",
                    fillOpacity=0.8,
                    weight=2,
                ).add_to(map_obj)
                processed_locations.add(to_coords_tuple)


@st.cache_data
def get_unique_teams(df):
    """Extract unique team names from departure and arrival columns"""
    teams = set(df["departure"].unique()) | set(df["arrival"].unique())
    return sorted(list(teams))


def parse_route_details(route_details_str):
    """Safely parse route_details string (can be dict string or already dict)"""
    if pd.isna(route_details_str) or route_details_str == "":
        return None
    try:
        # Try to evaluate as Python literal (dict string)
        if isinstance(route_details_str, str):
            # Replace single quotes with double quotes for JSON parsing if needed
            try:
                return ast.literal_eval(route_details_str)
            except (ValueError, SyntaxError):
                # If that fails, try JSON
                try:
                    return json.loads(route_details_str.replace("'", '"'))
                except (json.JSONDecodeError, ValueError):
                    return str(route_details_str)
        return route_details_str
    except (ValueError, TypeError, AttributeError):
        return str(route_details_str)


def find_route(df, departure, arrival):
    """Find route in dataframe (bidirectional)"""
    # Try both directions
    route = df[(df["departure"] == departure) & (df["arrival"] == arrival)]
    if route.empty:
        route = df[(df["departure"] == arrival) & (df["arrival"] == departure)]
    return route.iloc[0] if not route.empty else None


def format_time(seconds):
    """Format seconds into human-readable time"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}min"
    return f"{minutes}min"


def format_route_details(details, transport_type):
    """Format route details for display"""
    if not details:
        return "No route details available"

    if isinstance(details, str):
        return details

    output = []

    if transport_type == "car":
        if "one_way_distance_km" in details:
            output.append(
                f"**One-way distance:** {details['one_way_distance_km']:.2f} km"
            )
            output.append(
                f"**One-way duration:** {format_time(details.get('one_way_duration_seconds', 0))}"
            )
            output.append(
                f"**One-way emissions:** {details.get('one_way_emissions_kg_co2', 0):.2f} kg CO₂"
            )

        if "travel_steps" in details:
            output.append("\n**Travel Steps:**")
            for i, step in enumerate(details["travel_steps"], 1):
                output.append(f"\n{i}. {step.get('step_type', 'unknown').upper()}")
                output.append(f"   From: {step.get('from', 'N/A')}")
                output.append(f"   To: {step.get('to', 'N/A')}")
                output.append(f"   Distance: {step.get('distance_km', 0):.2f} km")
                output.append(
                    f"   Time: {format_time(step.get('travel_time_seconds', 0))}"
                )
                output.append(
                    f"   Emissions: {step.get('emissions_kg_co2', 0):.2f} kg CO₂"
                )

    elif transport_type == "train":
        if "train_route_details" in details:
            output.append("**Train Route Details:**")
            for i, leg in enumerate(details["train_route_details"], 1):
                output.append(
                    f"\n{i}. {leg.get('from', 'N/A')} → {leg.get('to', 'N/A')}"
                )
                output.append(f"   Type: {leg.get('type', 'N/A')}")
                output.append(f"   Distance: {leg.get('distance_km', 0):.2f} km")
                output.append(f"   Time: {format_time(leg.get('time_s', 0))}")
                output.append(f"   CO₂: {leg.get('co2_kg', 0):.4f} kg")

        if "car_route_details" in details:
            output.append("\n**Car Segments (to/from stations):**")
            if "segments" in details["car_route_details"]:
                for i, segment in enumerate(
                    details["car_route_details"]["segments"], 1
                ):
                    output.append(
                        f"\n{i}. {segment.get('from', 'N/A')} → {segment.get('to', 'N/A')}"
                    )
                    output.append(
                        f"   Distance: {segment.get('distance_km', 0):.2f} km"
                    )
                    output.append(
                        f"   Time: {format_time(segment.get('travel_time_seconds', 0))}"
                    )
                    output.append(
                        f"   Emissions: {segment.get('emissions_kg_co2', 0):.2f} kg CO₂"
                    )

    elif transport_type == "plane":
        if "one_way_flight_distance_km" in details:
            output.append(
                f"**One-way flight distance:** {details['one_way_flight_distance_km']:.2f} km"
            )
            output.append(
                f"**One-way flight time:** {format_time(details.get('one_way_flight_time_seconds', 0))}"
            )
            output.append(
                f"**One-way autocar distance:** {details.get('one_way_autocar_distance_km', 0):.2f} km"
            )
            output.append(
                f"**Fuel consumption:** {details.get('one_way_fuel_consumption_kg', 0):.2f} kg"
            )
            output.append(
                f"**Plane emissions:** {details.get('one_way_plane_emission_kg_co2', 0):.2f} kg CO₂"
            )
            output.append(
                f"**Autocar emissions:** {details.get('one_way_autocar_emission_kg_co2', 0):.2f} kg CO₂"
            )

        if "travel_steps" in details:
            output.append("\n**Travel Steps:**")
            for i, step in enumerate(details["travel_steps"], 1):
                output.append(f"\n{i}. {step.get('step_type', 'unknown').upper()}")
                output.append(f"   From: {step.get('from', 'N/A')}")
                output.append(f"   To: {step.get('to', 'N/A')}")
                if step.get("from_coords"):
                    output.append(f"   From Coords: {step['from_coords']}")
                if step.get("to_coords"):
                    output.append(f"   To Coords: {step['to_coords']}")
                output.append(f"   Distance: {step.get('distance_km', 0):.2f} km")
                output.append(
                    f"   Time: {format_time(step.get('travel_time_seconds', 0))}"
                )

        if "added_details" in details:
            output.append(f"\n**Notes:** {details['added_details']}")

    return "\n".join(output) if output else json.dumps(details, indent=2)


def main():
    st.title("⚽ Ligue 1 Route Comparison Tool")
    st.markdown(
        "Compare car, train, and plane routes between teams to verify calculations"
    )

    # Load data
    try:
        car_df, train_df, flight_df = load_data()
        stadium_df = load_stadium_data()
        gare_df = load_gare_data()
        gare_cache_df = load_gare_cache_data()
    except (FileNotFoundError, pd.errors.EmptyDataError, ValueError) as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    # Get unique teams
    all_teams = get_unique_teams(car_df)

    # Sidebar for team selection
    st.sidebar.header("Route Selection")

    mode = st.sidebar.radio(
        "Selection mode:", ["Single Team (all routes)", "Between Two Teams"]
    )

    if mode == "Single Team (all routes)":
        selected_team = st.sidebar.selectbox("Select a team:", all_teams)
        departure = selected_team
        arrival = None
    else:
        departure = st.sidebar.selectbox("Departure Team:", all_teams, key="departure")
        arrival = st.sidebar.selectbox("Arrival Team:", all_teams, key="arrival")

        if departure == arrival:
            st.sidebar.warning("⚠️ Please select different teams")
            st.stop()

    # Main content
    if mode == "Single Team (all routes)":
        st.header(f"All routes from/to {selected_team}")

        # Get all routes for this team
        car_routes = car_df[
            (car_df["departure"] == selected_team)
            | (car_df["arrival"] == selected_team)
        ]

        # Create comparison table
        routes_data = []
        for _, route in car_routes.iterrows():
            other_team = (
                route["arrival"]
                if route["departure"] == selected_team
                else route["departure"]
            )
            routes_data.append(
                {
                    "Team": other_team,
                    "Car Distance (km)": route["distance_km"],
                    "Car Time": format_time(route["travel_time_seconds"]),
                    "Car CO₂ (kg)": route["emissions_kg_co2"],
                    "Train Distance (km)": None,
                    "Train Time": None,
                    "Train CO₂ (kg)": None,
                    "Plane Distance (km)": None,
                    "Plane Time": None,
                    "Plane CO₂ (kg)": None,
                }
            )

            # Add train data
            train_route = find_route(train_df, selected_team, other_team)
            if train_route is not None:
                routes_data[-1]["Train Distance (km)"] = train_route["distance_km"]
                routes_data[-1]["Train Time"] = format_time(
                    train_route["travel_time_seconds"]
                )
                routes_data[-1]["Train CO₂ (kg)"] = train_route["emissions_kg_co2"]

            # Add plane data
            plane_route = find_route(flight_df, selected_team, other_team)
            if plane_route is not None:
                routes_data[-1]["Plane Distance (km)"] = plane_route["distance_km"]
                routes_data[-1]["Plane Time"] = format_time(
                    plane_route["travel_time_seconds"]
                )
                routes_data[-1]["Plane CO₂ (kg)"] = plane_route["emissions_kg_co2"]

        comparison_df = pd.DataFrame(routes_data)
        st.dataframe(comparison_df, use_container_width=True)

        # Detailed view for selected route
        st.subheader("Detailed Route Information")
        selected_route_team = st.selectbox(
            "Select a route to view details:", [r["Team"] for r in routes_data]
        )

        # Show details for selected route
        car_route = find_route(car_df, selected_team, selected_route_team)
        train_route = find_route(train_df, selected_team, selected_route_team)
        plane_route = find_route(flight_df, selected_team, selected_route_team)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("🚗 Car")
            if car_route is not None:
                st.metric("Total Distance", f"{car_route['distance_km']:.2f} km")
                st.metric("Total Time", format_time(car_route["travel_time_seconds"]))
                st.metric("Total CO₂", f"{car_route['emissions_kg_co2']:.2f} kg")

                with st.expander("Route Details"):
                    details = parse_route_details(car_route["route_details"])
                    st.text(format_route_details(details, "car"))
            else:
                st.warning("No route found")

        with col2:
            st.subheader("🚂 Train")
            if train_route is not None:
                st.metric("Total Distance", f"{train_route['distance_km']:.2f} km")
                st.metric("Total Time", format_time(train_route["travel_time_seconds"]))
                st.metric("Total CO₂", f"{train_route['emissions_kg_co2']:.2f} kg")

                with st.expander("Route Details"):
                    details = parse_route_details(train_route["route_details"])
                    st.text(format_route_details(details, "train"))
            else:
                st.warning("No route found")

        with col3:
            st.subheader("✈️ Plane")
            if plane_route is not None:
                st.metric("Total Distance", f"{plane_route['distance_km']:.2f} km")
                st.metric("Total Time", format_time(plane_route["travel_time_seconds"]))
                st.metric("Total CO₂", f"{plane_route['emissions_kg_co2']:.2f} kg")

                with st.expander("Route Details"):
                    details = parse_route_details(plane_route["route_details"])
                    st.text(format_route_details(details, "plane"))
            else:
                st.warning("No route found")

    else:  # Between Two Teams
        st.header(f"Route Comparison: {departure} ↔ {arrival}")

        # Find routes
        car_route = find_route(car_df, departure, arrival)
        train_route = find_route(train_df, departure, arrival)
        plane_route = find_route(flight_df, departure, arrival)

        # Comparison metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("🚗 Car")
            if car_route is not None:
                st.metric("Total Distance", f"{car_route['distance_km']:.2f} km")
                st.metric("Total Time", format_time(car_route["travel_time_seconds"]))
                st.metric("Total CO₂", f"{car_route['emissions_kg_co2']:.2f} kg")
            else:
                st.warning("No route found")

        with col2:
            st.subheader("🚂 Train")
            if train_route is not None:
                st.metric("Total Distance", f"{train_route['distance_km']:.2f} km")
                st.metric("Total Time", format_time(train_route["travel_time_seconds"]))
                st.metric("Total CO₂", f"{train_route['emissions_kg_co2']:.2f} kg")
            else:
                st.warning("No route found")

        with col3:
            st.subheader("✈️ Plane")
            if plane_route is not None:
                st.metric("Total Distance", f"{plane_route['distance_km']:.2f} km")
                st.metric("Total Time", format_time(plane_route["travel_time_seconds"]))
                st.metric("Total CO₂", f"{plane_route['emissions_kg_co2']:.2f} kg")
            else:
                st.warning("No route found")

        # Comparison table
        st.subheader("Comparison Table")
        comparison_data = []
        if car_route is not None:
            comparison_data.append(
                {
                    "Transport": "Car",
                    "Distance (km)": car_route["distance_km"],
                    "Time": format_time(car_route["travel_time_seconds"]),
                    "CO₂ (kg)": car_route["emissions_kg_co2"],
                }
            )
        if train_route is not None:
            comparison_data.append(
                {
                    "Transport": "Train",
                    "Distance (km)": train_route["distance_km"],
                    "Time": format_time(train_route["travel_time_seconds"]),
                    "CO₂ (kg)": train_route["emissions_kg_co2"],
                }
            )
        if plane_route is not None:
            comparison_data.append(
                {
                    "Transport": "Plane",
                    "Distance (km)": plane_route["distance_km"],
                    "Time": format_time(plane_route["travel_time_seconds"]),
                    "CO₂ (kg)": plane_route["emissions_kg_co2"],
                }
            )

        if comparison_data:
            comp_df = pd.DataFrame(comparison_data)
            st.dataframe(comp_df, use_container_width=True)

        # Map visualization
        st.subheader("🗺️ Route Map")
        if car_route is not None or train_route is not None or plane_route is not None:
            route_map = create_route_map(
                car_route,
                train_route,
                plane_route,
                departure,
                arrival,
                stadium_df,
                gare_df,
                gare_cache_df,
            )
            st_folium(route_map, width=1200, height=600)
        else:
            st.info("No routes available to display on map")

        # Detailed route information
        st.subheader("Detailed Route Information")

        tabs = st.tabs(["Car Details", "Train Details", "Plane Details"])

        with tabs[0]:
            if car_route is not None:
                st.write(f"**From:** {car_route['departure']}")
                st.write(f"**To:** {car_route['arrival']}")
                details = parse_route_details(car_route["route_details"])
                st.text(format_route_details(details, "car"))
            else:
                st.info("No car route available for this pair")

        with tabs[1]:
            if train_route is not None:
                st.write(f"**From:** {train_route['departure']}")
                st.write(f"**To:** {train_route['arrival']}")
                details = parse_route_details(train_route["route_details"])
                st.text(format_route_details(details, "train"))
            else:
                st.info("No train route available for this pair")

        with tabs[2]:
            if plane_route is not None:
                st.write(f"**From:** {plane_route['departure']}")
                st.write(f"**To:** {plane_route['arrival']}")
                details = parse_route_details(plane_route["route_details"])
                st.text(format_route_details(details, "plane"))
            else:
                st.info("No plane route available for this pair")


if __name__ == "__main__":
    main()
