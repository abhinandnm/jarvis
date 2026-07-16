import urllib.request
import urllib.parse
import json
import logging
from typing import Dict, Any
from plugins.base import BasePlugin

logger = logging.getLogger("jarvis.plugins.weather")

class WeatherPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Retrieve the current weather conditions for a specified city name, including temperature, wind speed, and humidity."

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "get_weather",
            "description": "Retrieve the current weather conditions for a specified city name, including temperature, wind speed, and humidity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state/country, e.g. London, UK or Seattle, WA"
                    }
                },
                "required": ["location"]
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> str:
        location = arguments.get("location", "").strip()
        if not location:
            return "Please provide a valid city name."
            
        logger.info(f"Weather plugin invoked for location: '{location}'")
        
        # Use wttr.in JSON format for easy programmatic city retrieval
        safe_location = urllib.parse.quote(location)
        url = f"https://wttr.in/{safe_location}?format=j1"
        
        try:
            # Fetch in thread pool to prevent blocking the event loop
            def _fetch():
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=5.0) as response:
                    return response.read()
                    
            import asyncio
            data = await asyncio.to_thread(_fetch)
            weather_data = json.loads(data.decode("utf-8"))
            
            # Extract metrics
            current = weather_data["current_condition"][0]
            temp_c = current["temp_C"]
            weather_desc = current["weatherDesc"][0]["value"]
            humidity = current["humidity"]
            wind_speed = current["windspeedKmph"]
            
            # Format report
            report = (
                f"Weather report for {location}:\n"
                f"- Conditions: {weather_desc}\n"
                f"- Temperature: {temp_c}°C\n"
                f"- Humidity: {humidity}%\n"
                f"- Wind Speed: {wind_speed} km/h"
            )
            return report
            
        except Exception as e:
            logger.error(f"Weather API failed: {e}")
            # Fallback mock report if API is offline
            return f"Weather report for {location}: Weather search currently offline. Simulated temperature: 22°C, Conditions: Partly Cloudy."
