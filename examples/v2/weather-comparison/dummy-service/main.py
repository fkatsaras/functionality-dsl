"""
Dummy Weather Service - Mock API for testing FDSL weather comparison
Provides forecast resources for Thessaloniki and London
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Dummy Weather Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock forecast data for Thessaloniki
THESSALONIKI_FORECAST = {
    "city": "thessaloniki",
    "latitude": 40.64,
    "longitude": 22.94,
    "timezone": "Europe/Athens",
    "hourly": {
        "time": [
            "2025-12-24T00:00", "2025-12-24T01:00", "2025-12-24T02:00",
            "2025-12-24T03:00", "2025-12-24T04:00", "2025-12-24T05:00",
            "2025-12-24T06:00", "2025-12-24T07:00", "2025-12-24T08:00",
            "2025-12-24T09:00", "2025-12-24T10:00", "2025-12-24T11:00",
        ],
        "temperature_2m": [8.5, 7.8, 7.2, 6.9, 6.5, 6.8, 7.5, 9.2, 12.3, 15.6, 18.4, 20.1],
        "relative_humidity_2m": [75, 78, 80, 82, 83, 81, 78, 72, 65, 58, 52, 48],
    }
}

# Mock forecast data for London
LONDON_FORECAST = {
    "city": "london",
    "latitude": 51.5072,
    "longitude": -0.1276,
    "timezone": "Europe/London",
    "hourly": {
        "time": [
            "2025-12-24T00:00", "2025-12-24T01:00", "2025-12-24T02:00",
            "2025-12-24T03:00", "2025-12-24T04:00", "2025-12-24T05:00",
            "2025-12-24T06:00", "2025-12-24T07:00", "2025-12-24T08:00",
            "2025-12-24T09:00", "2025-12-24T10:00", "2025-12-24T11:00",
        ],
        "temperature_2m": [5.2, 4.8, 4.3, 4.1, 3.9, 4.2, 5.1, 6.8, 9.2, 11.5, 13.8, 15.2],
        "relative_humidity_2m": [85, 87, 88, 89, 90, 88, 85, 80, 73, 68, 62, 58],
    }
}


@app.get("/forecasts/{city}")
async def get_forecast(city: str):
    """Get forecast for a specific city."""
    if city == "thessaloniki":
        return THESSALONIKI_FORECAST
    elif city == "london":
        return LONDON_FORECAST
    else:
        raise HTTPException(status_code=404, detail=f"Forecast for city '{city}' not found")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "dummy-weather-service"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
