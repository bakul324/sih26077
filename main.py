from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import math
import random


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="SIH26077 - AI-Driven Hyper-Local Early Warning System",
    description="Prototype backend for severe weather nowcasting and early warning.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# MODELS
# =========================================================

class LocationInput(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class WeatherInput(BaseModel):
    latitude: float = Field(23.55, ge=-90, le=90)
    longitude: float = Field(87.29, ge=-180, le=180)

    temperature: float = 31.0
    humidity: float = 88.0
    rainfall: float = 18.0
    wind_speed: float = 24.0
    pressure: float = 1004.0
    cape: float = 1650.0

    dewpoint: Optional[float] = None
    visibility: Optional[float] = None


# =========================================================
# HELPERS
# =========================================================

def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def safe_float(value, default=0.0):
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def risk_level(score):
    if score >= 75:
        return "EXTREME"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    if score >= 20:
        return "LOW"
    return "MINIMAL"


def alert_severity(score):
    if score >= 75:
        return "RED ALERT"
    if score >= 60:
        return "WARNING"
    if score >= 40:
        return "WATCH"
    return "NORMAL"


def calculate_thunderstorm(weather):
    humidity = safe_float(weather.humidity)
    cape = safe_float(weather.cape)
    wind = safe_float(weather.wind_speed)
    pressure = safe_float(weather.pressure)

    score = (
        humidity * 0.30
        + clamp(cape / 30) * 0.45
        + clamp(wind * 1.5) * 0.15
        + clamp((1015 - pressure) * 2) * 0.10
    )

    return round(clamp(score), 1)


def calculate_cloudburst(weather):
    humidity = safe_float(weather.humidity)
    rain = safe_float(weather.rainfall)
    cape = safe_float(weather.cape)

    score = (
        humidity * 0.35
        + clamp(rain * 3) * 0.40
        + clamp(cape / 25) * 0.25
    )

    return round(clamp(score), 1)


def calculate_flash_flood(weather):
    humidity = safe_float(weather.humidity)
    rain = safe_float(weather.rainfall)
    pressure = safe_float(weather.pressure)

    score = (
        humidity * 0.30
        + clamp(rain * 3.2) * 0.55
        + clamp((1015 - pressure) * 2) * 0.15
    )

    return round(clamp(score), 1)


def calculate_heavy_rain(weather):
    humidity = safe_float(weather.humidity)
    rain = safe_float(weather.rainfall)

    score = (
        humidity * 0.35
        + clamp(rain * 3.5) * 0.65
    )

    return round(clamp(score), 1)


def calculate_heat(weather):
    temperature = safe_float(weather.temperature)
    humidity = safe_float(weather.humidity)

    temp_score = clamp((temperature - 25) * 12)
    humidity_score = clamp((humidity - 50) * 1.2)

    return round(clamp(temp_score * 0.75 + humidity_score * 0.25), 1)


def calculate_wind(weather):
    wind = safe_float(weather.wind_speed)

    return round(clamp(wind * 2.5), 1)


# =========================================================
# RISK ENGINE
# =========================================================

def calculate_risk(weather):

    thunderstorm = calculate_thunderstorm(weather)
    cloudburst = calculate_cloudburst(weather)
    flash_flood = calculate_flash_flood(weather)
    heavy_rain = calculate_heavy_rain(weather)
    heat = calculate_heat(weather)
    wind = calculate_wind(weather)

    hazards = {
        "Thunderstorm": thunderstorm,
        "Cloudburst": cloudburst,
        "Flash Flood": flash_flood,
        "Heavy Rain": heavy_rain,
        "Heat": heat,
        "Wind": wind,
    }

    dominant_hazard = max(hazards, key=hazards.get)
    overall = round(
        max(hazards.values()) * 0.60
        + (
            thunderstorm
            + cloudburst
            + flash_flood
            + heavy_rain
        ) / 4 * 0.40,
        1
    )

    overall = clamp(overall)

    level = risk_level(overall)
    severity = alert_severity(overall)

    if overall >= 75:
        warning = (
            "Extreme severe-weather conditions detected. "
            "Immediate protective action is recommended."
        )
        recommendation = (
            "Move to a safe enclosed location. Avoid low-lying areas, "
            "open fields, trees, rivers and unstable structures."
        )

    elif overall >= 60:
        warning = (
            "High severe-weather risk detected for the selected location."
        )
        recommendation = (
            "Stay indoors where possible and monitor official warnings. "
            "Avoid unnecessary travel and waterlogged areas."
        )

    elif overall >= 40:
        warning = (
            "Moderate weather risk detected. Conditions may intensify."
        )
        recommendation = (
            "Remain alert and monitor weather conditions during the next few hours."
        )

    else:
        warning = "No major severe-weather threat detected at this time."
        recommendation = (
            "Continue normal activities while monitoring weather updates."
        )

    return {
        "overall": round(overall, 1),
        "risk_level": level,
        "dominant_hazard": dominant_hazard,
        "alert_severity": severity,

        "hazards": {
            "thunderstorm": thunderstorm,
            "cloudburst": cloudburst,
            "flash_flood": flash_flood,
            "heavy_rain": heavy_rain,
            "heat": heat,
            "wind": wind,
        },

        "warning": warning,
        "recommendation": recommendation,

        "confidence": round(
            clamp(72 + overall * 0.20),
            1
        ),

        "xai": {
            "humidity": humidity_message(weather),
            "rainfall": rainfall_message(weather),
            "cape": cape_message(weather),
            "pressure": pressure_message(weather),
            "wind": wind_message(weather),
        }
    }


# =========================================================
# XAI HELPERS
# =========================================================

def humidity_message(weather):
    humidity = safe_float(weather.humidity)

    if humidity >= 85:
        return "Very high moisture availability is increasing convective potential."
    if humidity >= 70:
        return "High humidity indicates elevated atmospheric moisture."
    return "Humidity is not currently a major risk driver."


def rainfall_message(weather):
    rain = safe_float(weather.rainfall)

    if rain >= 25:
        return "Heavy rainfall intensity is contributing strongly to flood risk."
    if rain >= 10:
        return "Rainfall is contributing to precipitation-related risk."
    return "Current rainfall intensity is relatively limited."


def cape_message(weather):
    cape = safe_float(weather.cape)

    if cape >= 2000:
        return "Very high CAPE indicates strong atmospheric instability."
    if cape >= 1000:
        return "Elevated CAPE indicates moderate-to-high convective instability."
    return "CAPE indicates limited convective instability."


def pressure_message(weather):
    pressure = safe_float(weather.pressure)

    if pressure < 1005:
        return "Lower pressure supports enhanced weather-system activity."
    return "Pressure is not currently a dominant risk factor."


def wind_message(weather):
    wind = safe_float(weather.wind_speed)

    if wind >= 40:
        return "Strong winds significantly increase severe-weather impacts."
    if wind >= 20:
        return "Moderate-to-strong winds may accompany convective activity."
    return "Wind speed is currently relatively low."


# =========================================================
# DEMO WEATHER
# =========================================================

def demo_weather(latitude, longitude):

    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature": 31.0,
        "humidity": 88.0,
        "rainfall": 18.0,
        "wind_speed": 24.0,
        "pressure": 1004.0,
        "cape": 1650.0,
        "dewpoint": 27.5,
        "visibility": 7.5,
        "source": "Prototype / Demo Data"
    }


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "project": "SIH26077",
        "name": "AI-Driven Hyper-Local Early Warning System",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SIH26077 backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/health")
def api_health():
    return {
        "status": "online",
        "backend": "healthy",
        "model": "prototype-ready",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/status")
def api_status():
    return {
        "backend": "online",
        "database": "prototype",
        "model": "ready",
        "satellite": "READY FOR INTEGRATION",
        "imdaa": "READY FOR INTEGRATION",
        "dem": "READY FOR INTEGRATION",
        "satellite_qpe": "READY FOR INTEGRATION"
    }


# =========================================================
# TEST
# =========================================================

@app.get("/api/test")
def api_test():
    return {
        "success": True,
        "message": "SIH26077 API is working correctly."
    }


# =========================================================
# LOCATION VALIDATION
# =========================================================

@app.post("/api/location/validate")
def validate_location(location: LocationInput):

    return {
        "valid": True,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "message": "Location accepted."
    }


# =========================================================
# PREDICTION
# =========================================================

@app.post("/api/predict")
def predict(weather: WeatherInput):

    real_weather = {
        "latitude": weather.latitude,
        "longitude": weather.longitude,
        "temperature": weather.temperature,
        "humidity": weather.humidity,
        "rainfall": weather.rainfall,
        "wind_speed": weather.wind_speed,
        "pressure": weather.pressure,
        "cape": weather.cape,
        "dewpoint": weather.dewpoint,
        "visibility": weather.visibility,
        "source": "Prototype Input"
    }

    prediction = calculate_risk(weather)

    return {
        "success": True,
        "real_weather": real_weather,
        "prediction": prediction,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =========================================================
# LOCATION PREDICTION
# =========================================================

@app.post("/api/location-predict")
def location_predict(location: LocationInput):

    weather_data = demo_weather(
        location.latitude,
        location.longitude
    )

    weather = WeatherInput(
        latitude=location.latitude,
        longitude=location.longitude,
        temperature=weather_data["temperature"],
        humidity=weather_data["humidity"],
        rainfall=weather_data["rainfall"],
        wind_speed=weather_data["wind_speed"],
        pressure=weather_data["pressure"],
        cape=weather_data["cape"],
        dewpoint=weather_data["dewpoint"],
        visibility=weather_data["visibility"]
    )

    prediction = calculate_risk(weather)

    return {
        "success": True,
        "real_weather": weather_data,
        "prediction": prediction,
        "data_mode": "DEMO / PROTOTYPE",
        "message": (
            "Prototype prediction generated. "
            "Live INSAT/IMDAA integration can be connected here."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =========================================================
# FORECAST
# =========================================================

@app.get("/api/forecast")
def forecast(
    latitude: float = Query(23.55, ge=-90, le=90),
    longitude: float = Query(87.29, ge=-180, le=180)
):

    base_temp = 31.0
    base_humidity = 88.0

    forecast_data = []

    for hour in range(0, 25):

        temperature = round(
            base_temp
            + math.sin(hour / 24 * math.pi * 2) * 3,
            1
        )

        humidity = round(
            clamp(
                base_humidity
                - math.sin(hour / 24 * math.pi * 2) * 8
            ),
            1
        )

        rain_probability = round(
            clamp(
                35
                + 30 * math.sin((hour + 4) / 24 * math.pi * 2)
            ),
            1
        )

        wind = round(
            18 + 8 * abs(math.sin(hour / 24 * math.pi)),
            1
        )

        forecast_data.append({
            "hour": hour,
            "temperature": temperature,
            "humidity": humidity,
            "rain_probability": rain_probability,
            "wind_speed": wind
        })

    return {
        "success": True,
        "latitude": latitude,
        "longitude": longitude,
        "hours": forecast_data,
        "source": "Prototype Forecast Engine"
    }


# =========================================================
# FORECAST STATISTICS
# =========================================================

@app.get("/api/forecast/statistics")
def forecast_statistics(
    latitude: float = Query(23.55),
    longitude: float = Query(87.29)
):

    forecast_response = forecast(latitude, longitude)
    data = forecast_response["hours"]

    temperatures = [x["temperature"] for x in data]
    rain_probabilities = [x["rain_probability"] for x in data]

    return {
        "success": True,
        "temperature_min": min(temperatures),
        "temperature_max": max(temperatures),
        "average_temperature": round(
            sum(temperatures) / len(temperatures),
            1
        ),
        "maximum_rain_probability": max(rain_probabilities),
        "average_rain_probability": round(
            sum(rain_probabilities) / len(rain_probabilities),
            1
        )
    }


# =========================================================
# ALERTS
# =========================================================

@app.get("/api/alerts")
def alerts():

    return {
        "success": True,
        "alerts": [
            {
                "id": "ALT-001",
                "severity": "WARNING",
                "hazard": "Heavy Rain",
                "message": "Heavy rainfall risk detected.",
                "status": "ACTIVE"
            },
            {
                "id": "ALT-002",
                "severity": "WATCH",
                "hazard": "Thunderstorm",
                "message": "Thunderstorm development possible.",
                "status": "MONITORING"
            }
        ]
    }


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/api/dashboard")
def dashboard():

    weather = WeatherInput()
    prediction = calculate_risk(weather)

    return {
        "success": True,
        "weather": demo_weather(
            weather.latitude,
            weather.longitude
        ),
        "prediction": prediction,
        "system": {
            "backend": "ONLINE",
            "api": "ONLINE",
            "model": "READY",
            "satellite": "READY FOR INTEGRATION",
            "imdaa": "READY FOR INTEGRATION",
            "dem": "READY FOR INTEGRATION"
        }
    }


# =========================================================
# RISK GRID
# =========================================================

@app.get("/api/risk-grid")
def risk_grid(
    latitude: float = Query(23.55),
    longitude: float = Query(87.29)
):

    grid = []

    random.seed(26077)

    for row in range(5):
        for col in range(5):

            lat = latitude + (row - 2) * 0.02
            lon = longitude + (col - 2) * 0.02

            risk = round(
                clamp(
                    45
                    + random.uniform(-20, 30)
                ),
                1
            )

            grid.append({
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "risk": risk,
                "risk_level": risk_level(risk)
            })

    return {
        "success": True,
        "center": {
            "latitude": latitude,
            "longitude": longitude
        },
        "grid": grid
    }


# =========================================================
# RISK SUMMARY
# =========================================================

@app.get("/api/risk-summary")
def risk_summary():

    weather = WeatherInput()
    prediction = calculate_risk(weather)

    return {
        "overall_risk": prediction["overall"],
        "risk_level": prediction["risk_level"],
        "dominant_hazard": prediction["dominant_hazard"],
        "alert_severity": prediction["alert_severity"],
        "confidence": prediction["confidence"]
    }


# =========================================================
# FEATURES
# =========================================================

@app.get("/api/features")
def features():

    return {
        "features": [
            "Hyper-local risk prediction",
            "Thunderstorm detection",
            "Cloudburst detection",
            "Flash-flood risk",
            "Heavy-rain risk",
            "Heat risk",
            "Wind risk",
            "Explainable AI",
            "Dynamic risk mapping",
            "Automated early warning",
            "Emergency decision support",
            "Forecast generation",
            "Alert audit trail"
        ]
    }


# =========================================================
# PROJECT INFORMATION
# =========================================================

@app.get("/api/project")
def project():

    return {
        "id": "SIH26077",
        "title": "AI-Driven Hyper-Local Early Warning System for Severe Weather Nowcasting",
        "organization": "Ministry of Earth Sciences / NCMRWF",
        "category": "Disaster Management",
        "type": "Software",
        "lead_time": "2-6 hours",
        "status": "Prototype"
    }


# =========================================================
# DEBUG
# =========================================================

@app.get("/api/debug")
def debug():

    return {
        "python_backend": True,
        "fastapi": True,
        "uvicorn": True,
        "port": "Render $PORT compatible",
        "status": "OK"
    }


# =========================================================
# RUN LOCALLY
# =========================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8001,
        reload=True
    )