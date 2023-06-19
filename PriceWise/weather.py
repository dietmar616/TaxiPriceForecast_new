import requests

def get_weather(latitude, longitude):
    base_url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid=5af38c9b96aa534fcf9b5347f80eed59"
    response = requests.get(base_url)
    data = response.json()
    weather = data['weather'][0]['description']
    return weather
    
weather_coefficients = {
    'overcast clouds': 0.05,
    'mist': 0.1,
    'fog': 0.1,
    'light intensity drizzle': 0.15,
    'heavy intensity drizzle': 0.2,
    'light intensity drizzle rain': 0.15,
    'light rain': 0.1,
    'moderate rain': 0.2,
    'heavy intensity rain': 0.3,
    'light intensity shower rain': 0.2,
    'shower rain': 0.3,
    'light snow': 0.15,
    'snow': 0.2,
    'cold': 0.1,
    'hot': 0.1,
    'windy': 0.15,
    'hail': 0.2,
    'moderate breeze': 0.1,
    'fresh breeze': 0.15,
}