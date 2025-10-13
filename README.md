# Ligue1

There are three folder:
- One that would calculate the emissions emitted by planes (let's name it plane folder)
- One that would calculate the emissions emitted by train or a bus  (let's name it train folder)
- One that create the local website (let's name it website folder)

In the plane folder and the train folder, running only the master.py file would suffice. The other files shouldn't be touched unless you want to change something. There are two inputs for those two files to work: your google API, and the number of passengers that travel with the team. I have put for now 50, but this number should be refined.

For website folder, you need to run first get_excel_file.py and then run Building_a_website.py.

### Setting up the environment

1. **Install uv** (if not already installed):
   ```bash
   # On macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # On Windows (PowerShell)
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Restart your terminal** and navigate to the project root directory if you just installed uv

3. **Create a `.env` file** in the project root directory:
   ```bash
   touch .env
   ```
   
4. **Add the API key to your `.env` file**:
   ```
   GOOGLE_MAPS_API_KEY=your_api_key_here
   ```

5. **Install dependencies and create virtual environment**:
   ```bash
   uv sync
   ```

## Backend folder

The backend folder contains a refactored and modular version of the calculation logic:
- **services/**: Contains transport service classes for train, plane, and car emissions calculations
- **data/**: Stores calculated travel data and emission results
- **global_variables.py**: Configuration variables and emission factors

### Running the backend (if you need to recompute the travels)

To run the complete analysis using the backend services:

```bash
# Using uv (recommended)
uv run python -m scripts.retrieve_trajets
```

This script will:
1. Process train routes and save results to `train_emissions.csv`
2. Process plane routes and save results to `flight_emissions.csv` 
3. Process car routes and save results to `car_emissions.csv`