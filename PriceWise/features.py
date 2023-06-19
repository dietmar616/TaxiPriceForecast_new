import requests
from bs4 import BeautifulSoup
import openrouteservice as ors
import numpy as np
from datetime import timedelta

from .connection import connection

def get_fuel_price_for_df():
    return [44.22, 42.80, 21.08]

def get_fuel_price():
    url = "https://www.dexpens.com/FuelPrice/Khmelnytskyi%20Oblast"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    fuel_data = []
    table = soup.find_all('table', class_="table font-size-media") 
    for tab in table:
        body = tab.find_all('tbody')
        for tbody in body:
            rows = tbody.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                cols = [col.text.strip() for col in cols[1:4]]  
                fuel_data.append(cols)
    return fuel_data[0]

def calculate_distance(start_latitude, start_longitude, end_latitude, end_longitude):
    client = ors.Client(key='5b3ce3597851110001cf6248a6139d2c181b46b2992071e047de26cc')  # Replace with your OpenRouteService API key
    coords = [[start_longitude, start_latitude], [end_longitude, end_latitude]]
    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
    distance_meters = route['features'][0]['properties']['segments'][0]['distance']
    distance_kilometers = distance_meters / 1000
    return distance_kilometers

def get_driver_fuel_type(driver_id, get_fuel_price_func):
    with connection.cursor() as cursor:
        sql = "SELECT `fuel_type` FROM `drivers` WHERE `id` = %s"
        cursor.execute(sql, (driver_id,))
        result = cursor.fetchone()
        fuel_type = result['fuel_type'] if result else None

        fuel_prices = get_fuel_price_func()
        if fuel_type == 'Бензин':
            fuel_price = convert_fuel_price_to_float(fuel_prices[0])  
        elif fuel_type == 'Дизель':
            fuel_price = convert_fuel_price_to_float(fuel_prices[1])
        elif fuel_type == 'Газ':
            fuel_price = convert_fuel_price_to_float(fuel_prices[2])
        else:
            fuel_price = 0.0

        return fuel_price


def convert_fuel_price_to_float(fuel_price):
    if isinstance(fuel_price, str):
        return float(fuel_price.replace(',', '.'))
    return fuel_price

def get_driver_fuel_consumption(driver_id):
    with connection.cursor() as cursor:
        sql = "SELECT `fuel_consumption` FROM `drivers` WHERE `id` = %s"
        cursor.execute(sql, (driver_id,))
        result = cursor.fetchone()
        return result['fuel_consumption'] if result else None

def get_driver_comfort_level(driver_id):
    with connection.cursor() as cursor:
        sql = "SELECT `comfort_level` FROM `drivers` WHERE `id` = %s"
        cursor.execute(sql, (driver_id,))
        result = cursor.fetchone()
        return result['comfort_level'] if result else None
    
comfort_levels = {
    'Стандарт': {'start_price': 50, 'additional_price': 11},
    'Економ': {'start_price': 43, 'additional_price': 10},
    'Зручний': {'start_price': 56, 'additional_price': 12},
}

def generate_trip_time(start_date):
    hour = int(np.random.choice(np.arange(24), p=[
        0.02, # 0:00 - 0:59
        0.02, # 1:00 - 1:59
        0.025, # 2:00 - 2:59
        0.025, # 3:00 - 3:59
        0.025, # 4:00 - 4:59
        0.04,  # 5:00 - 5:59
        0.05,  # 6:00 - 6:59
        0.075, # 7:00 - 7:59
        0.075, # 8:00 - 8:59
        0.05,  # 9:00 - 9:59
        0.04,  # 10:00 - 10:59
        0.03,  # 11:00 - 11:59
        0.03,  # 12:00 - 12:59
        0.03,  # 13:00 - 13:59
        0.04,  # 14:00 - 14:59
        0.05,  # 15:00 - 15:59
        0.05,  # 16:00 - 16:59
        0.065, # 17:00 - 17:59
        0.065, # 18:00 - 18:59
        0.05,  # 19:00 - 19:59
        0.04,  # 20:00 - 20:59
        0.03,  # 21:00 - 21:59
        0.04,  # 22:00 - 22:59
        0.035  # 23:00 - 23:59
    ]))
    minute = int(np.random.randint(60))
    return start_date + timedelta(hours=hour, minutes=minute)

week_day_coefficients = {
    0: 0.9,  # Monday
    1: 0.95,  # Tuesday
    2: 0.95,  # Wednesday
    3: 0.95,  # Thursday
    4: 1.1,  # Friday
    5: 1.2,  # Saturday
    6: 1.1  # Sunday
}