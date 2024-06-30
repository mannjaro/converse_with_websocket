from pydantic import BaseModel, Field


class WeatherForecast(BaseModel):
    latitude: float = Field(..., description="Latitude for weather forcast api")
    longitude: float = Field(..., description="Longitude for weather forcast api")
    timezone: str = Field(..., description="Time zone", examples=["Asia/Tokyo"])


def get_weather(params: WeatherForecast):
    print(params)
    return "Rainy / Max: 24°C / Min: 18°C"
