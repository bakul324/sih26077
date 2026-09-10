import requests


def get_weather(latitude: float, longitude: float):
    """
    Prototype weather provider.
    Uses Open-Meteo public weather data.
    """

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "wind_speed_10m,"
            "surface_pressure"
        ),
        "timezone": "auto"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        current = data.get("current", {})

        return {
            "latitude": latitude,
            "longitude": longitude,
            "temperature": current.get("temperature_2m", 0),
            "humidity": current.get("relative_humidity_2m", 0),
            "rainfall": current.get("precipitation", 0),
            "wind_speed": current.get("wind_speed_10m", 0),
            "pressure": current.get("surface_pressure", 0),
            "cape": 0,
            "dewpoint": None,
            "visibility": None,
            "source": "Open-Meteo"
        }

    except Exception as error:

        return {
            "latitude": latitude,
            "longitude": longitude,
            "temperature": 31,
            "humidity": 80,
            "rainfall": 5,
            "wind_speed": 15,
            "pressure": 1010,
            "cape": 1000,
            "dewpoint": None,
            "visibility": None,
            "source": "Fallback Prototype Data",
            "error": str(error)
        }


def get_forecast(latitude: float, longitude: float):
    """
    Returns hourly forecast data for the next 24 hours.
    """

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation_probability,"
            "wind_speed_10m"
        ),
        "forecast_days": 2,
        "timezone": "auto"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        hourly = data.get("hourly", {})

        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        rain_probability = hourly.get(
            "precipitation_probability",
            []
        )
        wind = hourly.get("wind_speed_10m", [])

        result = []

        for i in range(min(24, len(times))):

            result.append({
                "time": times[i],
                "temperature": temperatures[i]
                if i < len(temperatures) else 0,

                "humidity": humidity[i]
                if i < len(humidity) else 0,

                "rain_probability": rain_probability[i]
                if i < len(rain_probability) else 0,

                "wind_speed": wind[i]
                if i < len(wind) else 0
            })

        return result

    except Exception:

        return []