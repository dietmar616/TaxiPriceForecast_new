from django.shortcuts import render
from django.http import JsonResponse
import requests
import folium
from datetime import datetime, timedelta
import pytz
from joblib import load
from django.http import JsonResponse
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from joblib import dump, load
import pandas as pd
import os
from random import uniform, randint, choices


from .connection import connection
from .weather import weather_coefficients, get_weather
from .features import comfort_levels, calculate_distance, get_driver_fuel_consumption, get_fuel_price, get_driver_fuel_type, get_driver_comfort_level, get_fuel_price_for_df, generate_trip_time, week_day_coefficients

def calculate_price(request):
    if request.method == 'POST':
        driver_id = float(request.POST.get('driver_id'))
        start_latitude = float(request.POST.get('start_latitude'))
        start_longitude = float(request.POST.get('start_longitude'))
        end_latitude = float(request.POST.get('end_latitude'))
        end_longitude = float(request.POST.get('end_longitude'))

        distance = calculate_distance(start_latitude, start_longitude, end_latitude, end_longitude)
        fuel_consumption = get_driver_fuel_consumption(driver_id)
        fuel_price = get_driver_fuel_type(driver_id, get_fuel_price)
        fuel_cost = fuel_consumption * distance * fuel_price / 100  # ділимо на 100, тому що fuel_consumption літрів на 100 км  

        weather = get_weather(end_latitude, end_longitude)
        weather_coefficient = weather_coefficients.get(weather, 0.0)

        comfort_level = get_driver_comfort_level(driver_id)
        comfort_data = comfort_levels.get(comfort_level, comfort_levels['Стандарт'])

        price = max(comfort_data['start_price'], comfort_data['start_price'] + (distance - 2) * comfort_data['additional_price']) 
        price_weather = price
        price_peak = price

        price_weather *= weather_coefficient

        tz_kyiv = pytz.timezone('Europe/Kiev')
        current_time = datetime.now(tz_kyiv)

        peak_hours = [(7, 9), (17, 19), (22, 7)]

        for start, end in peak_hours:
            peak_start = datetime.now(tz_kyiv).replace(hour=start, minute=0, second=0)
            peak_end = datetime.now(tz_kyiv).replace(hour=end, minute=0, second=0)
            if peak_end < peak_start:
                peak_end += timedelta(days=1)
            if peak_start <= current_time <= peak_end:
                price_peak *= 0.2  
            else:
                price_peak = 0

        price += price_weather + price_peak + fuel_cost

        m = folium.Map(location=[start_latitude, start_longitude], zoom_start=13)
        folium.Marker([start_latitude, start_longitude], popup='Start Location').add_to(m)
        folium.Marker([end_latitude, end_longitude], popup='End Location').add_to(m)

        coords = [[start_longitude, start_latitude], [end_longitude, end_latitude]]
        body = {"coordinates": coords}
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
            'Authorization': '5b3ce3597851110001cf6248a6139d2c181b46b2992071e047de26cc',
            'Content-Type': 'application/json; charset=utf-8'
        }
        response = requests.post('https://api.openrouteservice.org/v2/directions/driving-car/geojson', json=body, headers=headers)

        if response.status_code == 200:
            route_geojson = response.json()
        map_html = m.get_root().render()

        return JsonResponse({'map_html': map_html, 'price': price, 'route': route_geojson, 'distance': distance})
    return render(request, 'price_calculator.html', {})
    
def save_trip(request):
    if request.method == 'POST':
        driver_id = float(request.POST.get('driver_id'))
        start_latitude = float(request.POST.get('start_latitude'))
        start_longitude = float(request.POST.get('start_longitude'))
        end_latitude = float(request.POST.get('end_latitude'))
        end_longitude = float(request.POST.get('end_longitude'))
        distance = float(request.POST.get('distance'))
        price = float(request.POST.get('price'))

        weather = get_weather(end_latitude, end_longitude)
        fuel_price = get_driver_fuel_type(driver_id, get_fuel_price)

        tz_kyiv = pytz.timezone('Europe/Kiev')
        current_time = datetime.now(tz_kyiv)

        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO `trips` (`driver_id`, `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude`, `distance`, `weather`, `fuel_price`, `trip_time`,`price`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (driver_id, start_latitude, start_longitude, end_latitude, end_longitude, distance, weather, fuel_price, current_time, price))
                connection.commit()
                print("Trip data saved in the database")
        except Exception as e:
            print("Error:", e)

        return JsonResponse({'message': 'Trip saved successfully'})
    return JsonResponse({'error': 'Invalid request method'})

def addDriver(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        car_brand = request.POST.get('car_brand')
        car_model = request.POST.get('car_model')
        fuel_type = request.POST.get('fuel_type')
        comfort_level = request.POST.get('comfort_level')
        fuel_consumption = request.POST.get('fuel_consumption')
        if fuel_consumption is not None and fuel_consumption != '':
            fuel_consumption = float(fuel_consumption)
        else:
            fuel_consumption = 0.0  # or whatever default value you see fit
            
        fuel_type = request.POST.get('fuel_type')
        if fuel_type is None or fuel_type == '':
            return JsonResponse({'error': 'Fuel type is required'})
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO `drivers` (`name`, `car_brand`, `car_model`, `fuel_consumption`, `fuel_type`, `comfort_level`) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (name, car_brand, car_model, fuel_consumption, fuel_type, comfort_level))
                connection.commit()
                print("Driver data saved in the database")
        except Exception as e:
            print("Error:", e)

        return JsonResponse({'message': 'Driver added successfully'})
    return JsonResponse({'error': 'Invalid request method'})

def loadDrivers(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT `id`, `name`, `car_brand`, `car_model`, `comfort_level` FROM `drivers`")
            drivers = cursor.fetchall()
            driver_list = [{'id': driver['id'], 'name': driver['name'], 'car_brand': driver['car_brand'], 'car_model': driver['car_model'], 'comfort_level' : driver['comfort_level']} for driver in drivers]
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'error': 'Could not load drivers'})
    return JsonResponse({'drivers': driver_list})

def create_df(request):
    file_path = 'D:\\MySQL_data\\_Diploma\\Genetaion_df\\synthetic_data.csv'

    df = pd.DataFrame(columns=['driver_id', 'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude', 'start_time', 'distance', 'weather', 'comfort_level', 'price'])

    data = []

    start_date = datetime(2022, 6, 14)   
    end_date = datetime(2023, 6, 14)

    while start_date <= end_date:
        for _ in range(randint(100, 200)):
            driver_id = randint(1, 21)

            start_latitude = uniform(49.4005, 49.4567)
            start_longitude = uniform(26.9237, 27.0077)
            end_latitude = uniform(49.4005, 49.4567)
            end_longitude = uniform(26.9237, 27.0077)
            weather = choices(list(weather_coefficients.keys()), weights=weather_coefficients.values())[0]
            distance = round(uniform(1, 11), 2)  

            fuel_consumption = get_driver_fuel_consumption(driver_id)
            fuel_price = get_driver_fuel_type(driver_id, get_fuel_price_for_df)
            fuel_cost = fuel_consumption * distance * fuel_price / 100

            comfort_level = get_driver_comfort_level(driver_id)
            comfort_data = comfort_levels.get(comfort_level, comfort_levels['Стандарт'])

            price = max(comfort_data['start_price'], comfort_data['start_price'] + (distance - 2) * comfort_data['additional_price'])

            price_peak = price

            peak_hours = [(7, 9), (17, 19)]

            trip_time = generate_trip_time(start_date)

            for start, end in peak_hours:
                peak_start = trip_time.replace(hour=start, minute=0, second=0)
                peak_end = trip_time.replace(hour=end, minute=0, second=0)
                if peak_end < peak_start:
                    peak_end += timedelta(days=1)
                if peak_start <= trip_time <= peak_end:
                    price_peak *= 0.2  
                else:
                    price_peak = 0

            price_weather = price * weather_coefficients[weather]

            price += price_weather + price_peak + fuel_cost

            day_of_week = trip_time.weekday()
            week_day_coefficient = week_day_coefficients[day_of_week]
            price *= week_day_coefficient

            data.append({
                        'driver_id': driver_id,
                        'start_latitude': start_latitude,
                        'start_longitude': start_longitude,
                        'end_latitude': end_latitude,
                        'end_longitude': end_longitude,
                        'start_time': trip_time,
                        'distance': distance,
                        'weather': weather,
                        'comfort_level': comfort_level,
                        'price': price
                    })
        start_date += timedelta(days=1)

    df = pd.DataFrame(data)
    if os.path.exists(file_path):
        os.remove(file_path)  
    df.to_csv(file_path, index=False)
    # Now we have our df, let's prepare the data and train the model
    df['start_time'] = pd.to_datetime(df['start_time'])
    # Then convert datetime to float (for example, number of seconds from a specific point in time, like Unix epoch)
    df['start_time'] = (df['start_time'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
    df.set_index('start_time', inplace=True)
    df.index = pd.to_datetime(df.index, unit='s')
    # Create peak_hour feature
    df['peak_hour'] = ((df.index.hour >= 7) & (df.index.hour <= 9) | 
                       (df.index.hour >= 17) & (df.index.hour <= 19)).astype(int)

    # Apply one-hot encoding to weather and comfort_level
    encoder = OneHotEncoder(sparse=False)
    encoded_features = encoder.fit_transform(df[['weather', 'comfort_level']])
    encoded_df = pd.DataFrame(encoded_features, columns=encoder.get_feature_names_out(['weather', 'comfort_level']))
    # Reset the index of both dataframes before concatenating
    df.reset_index(drop=True, inplace=True)
    encoded_df.reset_index(drop=True, inplace=True)
    # Concatenate original df with encoded features and remove original categorical features
    df = pd.concat([df, encoded_df], axis=1)
    df.drop(['weather', 'comfort_level'], axis=1, inplace=True)
    df.drop(['driver_id', 'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude'], axis=1, inplace=True)

    print(df.columns)
    # Now we can include more features for prediction
    X = df.drop('price', axis=1)
    y = df['price']
    # Split the data
    # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
    # Use Random Forest Regressor
    regressor = RandomForestRegressor(n_estimators=100, random_state=0)
    regressor.fit(X, y)
    # Save the encoder
    dump(encoder, 'encoder.joblib')
    # Save the model to a file
    dump(regressor, 'trained_model.joblib')

    return JsonResponse({'message': 'Dataframe created and model trained successfully.'})

def get_predictions(request):
    regressor = load('trained_model.joblib')
    encoder = load('encoder.joblib')

    days = int(request.GET.get('days', 7))

    start_date = datetime(2023, 6, 14)
    total_revenue = 0
    average_costs = []

    for _ in range(days):
        daily_data = []
        for _ in range(randint(100, 200)):
            driver_id = randint(1, 21)
            start_latitude = uniform(49.4005, 49.4567)
            start_longitude = uniform(26.9237, 27.0077)
            end_latitude = uniform(49.4005, 49.4567)
            end_longitude = uniform(26.9237, 27.0077)
            distance = round(uniform(1, 11), 2) 
            weather = choices(list(weather_coefficients.keys()), weights=weather_coefficients.values())[0]
            comfort_level = get_driver_comfort_level(driver_id)

            trip_time = generate_trip_time(start_date)
            day_of_week = trip_time.weekday()
            week_day_coefficient = week_day_coefficients[day_of_week]

            
            peak_hour = int((trip_time.hour >= 7) & (trip_time.hour <= 9) | (trip_time.hour >= 17) & (trip_time.hour <= 19))

            daily_data.append({
                        'driver_id': driver_id,
                        'start_latitude': start_latitude,
                        'start_longitude': start_longitude,
                        'end_latitude': end_latitude,
                        'end_longitude': end_longitude,
                        'distance': distance,
                        'weather': weather,
                        'comfort_level': comfort_level,
                        'peak_hour': peak_hour
                    })
        start_date_str = start_date.strftime('%Y-%m-%d')
        start_date += timedelta(days=1)

        daily_df = pd.DataFrame(daily_data)
        # Apply one-hot encoding to weather and comfort_level
        encoded_features = encoder.transform(daily_df[['weather', 'comfort_level']])
        encoded_df = pd.DataFrame(encoded_features, columns=encoder.get_feature_names_out(['weather', 'comfort_level']))
        # Reset the index of both dataframes before concatenating
        daily_df.reset_index(drop=True, inplace=True)
        encoded_df.reset_index(drop=True, inplace=True)
        # Concatenate original df with encoded features and remove original categorical features
        daily_df = pd.concat([daily_df, encoded_df], axis=1)
        daily_df.drop(['weather', 'comfort_level', 'driver_id', 'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude'], axis=1, inplace=True)

        # Get predictions
        y_pred = regressor.predict(daily_df)
        y_pred *= week_day_coefficient  # apply the weekday coefficient
        total_revenue += sum(y_pred)

        # Calculate average cost and add it to the list
        average_cost = sum(y_pred) / len(y_pred)
        average_costs.append({
            "date": start_date_str,
            "average_cost": average_cost
        })

    result = {
        'total_revenue': total_revenue,
        'average_costs': average_costs
    }

    return JsonResponse(result)


def predictions_page(request):
    return render(request, 'predictions_page.html')


