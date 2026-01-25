"""
Dummy Weather Service - Open-Meteo Compatible Format

Returns weather forecast data in Open-Meteo API format:
https://api.open-meteo.com/v1/forecast?latitude=40.64&longitude=22.94&hourly=temperature_2m,relative_humidity_2m

Endpoints:
- GET /forecast/{city} - Returns forecast for specified city
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import random

app = FastAPI(title="Dummy Weather Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# City coordinates (real locations)
CITIES = {
    "thessaloniki": {"latitude": 40.64, "longitude": 22.94},
    "london": {"latitude": 51.51, "longitude": -0.13},
    "athens": {"latitude": 37.98, "longitude": 23.73},
    "berlin": {"latitude": 52.52, "longitude": 13.41},
    "paris": {"latitude": 48.86, "longitude": 2.35},
}

def generate_hourly_data(city: str, hours: int = 24) -> dict:
    """Generate realistic hourly weather data"""
    now = datetime.utcnow()

    # Base temperatures by city (realistic averages)
    base_temps = {
        "thessaloniki": 22.0,
        "london": 15.0,
        "athens": 25.0,
        "berlin": 12.0,
        "paris": 16.0,
    }

    base_temp = base_temps.get(city.lower(), 18.0)

    times = []
    temperatures = []
    humidities = []

    for i in range(hours):
        # Generate timestamp
        timestamp = (now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00")
        times.append(timestamp)

        # Generate realistic temperature variation (sinusoidal pattern)
        hour_of_day = (now.hour + i) % 24
        # Temperature peaks around 14:00, lowest around 4:00
        daily_variation = 5 * ((hour_of_day - 4) / 10.0) if hour_of_day > 4 else -3
        temp = base_temp + daily_variation + random.uniform(-2, 2)
        temperatures.append(round(temp, 1))

        # Generate humidity (inverse correlation with temperature)
        humidity = 70 - (temp - base_temp) * 2 + random.uniform(-10, 10)
        humidities.append(round(max(20, min(95, humidity)), 0))

    return {
        "time": times,
        "temperature_2m": temperatures,
        "relative_humidity_2m": humidities,
    }

@app.get("/forecast/{city}")
async def get_forecast(city: str):
    """
    Get weather forecast for a city

    Returns Open-Meteo compatible format:
    {
      "latitude": 40.64,
      "longitude": 22.94,
      "hourly": {
        "time": ["2025-01-01T00:00", ...],
        "temperature_2m": [18.5, 19.2, ...],
        "relative_humidity_2m": [65, 63, ...]
      }
    }
    """
    city_lower = city.lower()

    if city_lower not in CITIES:
        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' not found. Available cities: {', '.join(CITIES.keys())}"
        )

    coords = CITIES[city_lower]
    hourly_data = generate_hourly_data(city_lower, hours=48)  # 48-hour forecast

    return {
        "city": city_lower,
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "hourly": hourly_data,
    }

@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "Dummy Weather Service",
        "format": "Open-Meteo Compatible",
        "available_cities": list(CITIES.keys()),
        "example": "/forecast/thessaloniki"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9003)
