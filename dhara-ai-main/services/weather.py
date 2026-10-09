import requests
import random

# In a real app, you would load this from config or environment variables
OPENWEATHER_API_KEY = "dummy_api_key_for_hackathon"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

def fetch_weather_data(district_name):
    """
    Fetches real-time weather data for a given district.
    If the API call fails or key is invalid, returns realistic mock data for the hackathon.
    """
    try:
        params = {
            "q": district_name,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        response = requests.get(BASE_URL, params=params, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            # Extract basic info
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            # OpenWeather sends rain data if available
            rain_1h = data.get('rain', {}).get('1h', 0)
            
            # Since we need 30-day deviation for the model, we mock the deviation 
            # based on current conditions just to show integration works.
            deviation = (rain_1h * 5) - 10 # Rough mapping to percentage deviation
            
            return {
                "success": True,
                "temperature_c": temp,
                "humidity": humidity,
                "rainfall_deviation": round(max(-50, min(50, deviation)), 1),
                "source": "OpenWeather API"
            }
        else:
            return mock_weather_data(district_name)
            
    except Exception as e:
        print(f"Weather API Error: {e}")
        return mock_weather_data(district_name)

def mock_weather_data(district_name):
    """Fallback mock data generation for demo purposes."""
    # Seed random with district name length to get consistent results per district
    random.seed(len(district_name) if district_name else 42)
    
    dev = random.uniform(-30, 30)
    temp = random.uniform(22, 38)
    humidity = random.uniform(40, 90)
    
    return {
        "success": False,
        "temperature_c": round(temp, 1),
        "humidity": round(humidity, 1),
        "rainfall_deviation": round(dev, 1),
        "source": "Mock Data (API Fallback)"
    }
