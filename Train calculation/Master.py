import pandas as pd
import subprocess

API_KEY='AIzaSyDIf4jaKso1v7WmOVfUyZCLBVYmcOJnuH4'
passengers="50"


subprocess.run(["python", "Get-coordinates.py", API_KEY])
subprocess.run(["python", "Get-train-steps.py",API_KEY])
subprocess.run(["python", "Get-coordinates-station.py",API_KEY])
subprocess.run(["python", "Get-car-steps.py",API_KEY])
subprocess.run(["python", "Get-car-trips.py",API_KEY])
subprocess.run(["python", "Calculate-clean-transport.py",passengers])
subprocess.run(["python", "Get-total-emissions-per-team.py"])
