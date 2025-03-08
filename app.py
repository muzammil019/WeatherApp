from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import time
from collections import deque
from datetime import datetime, timedelta
import math

load_dotenv()

app = Flask(__name__)
CORS(app)

# Weather API configuration
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
WEATHER_API_BASE_URL = "http://api.weatherapi.com/v1/current.json"
WEATHER_API_HISTORY_URL = "http://api.weatherapi.com/v1/history.json"

# Store historical data (last 6 hours)
MAX_HISTORY_POINTS = 72  # 6 hours * 12 points per hour (5-minute intervals)
weather_history = {
    'timestamps': deque(maxlen=MAX_HISTORY_POINTS),
    'temperature': deque(maxlen=MAX_HISTORY_POINTS),
    'humidity': deque(maxlen=MAX_HISTORY_POINTS),
    'dew_point': deque(maxlen=MAX_HISTORY_POINTS)
}

def calculate_dew_point(temp_c, humidity):
    # Magnus formula for dew point calculation
    a = 17.27
    b = 237.7
    try:
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity/100.0)
        return round((b * alpha) / (a - alpha), 2)
    except (ValueError, ZeroDivisionError):
        return 0

def update_weather_history(data):
    try:
        # Handle different timestamp formats
        try:
            # Try the standard format first
            current_time = datetime.strptime(data['local_time'], '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                # Try alternative format with seconds
                current_time = datetime.strptime(data['local_time'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # If all else fails, use current time
                current_time = datetime.now()
        
        # Calculate dew point if not already provided
        if 'dew_point_c' in data:
            dew_point = data['dew_point_c']
        else:
            dew_point = calculate_dew_point(data['temperature_c'], data['humidity'])
        
        # Only append if this timestamp doesn't exist
        if not any(t.strftime('%Y-%m-%d %H:%M') == current_time.strftime('%Y-%m-%d %H:%M') for t in weather_history['timestamps']):
            weather_history['timestamps'].append(current_time)
            weather_history['temperature'].append(round(data['temperature_c'], 2))
            weather_history['humidity'].append(data['humidity'])
            weather_history['dew_point'].append(dew_point)
            
            # Sort the data after each update
            timestamps = list(weather_history['timestamps'])
            temperatures = list(weather_history['temperature'])
            humidities = list(weather_history['humidity'])
            dew_points = list(weather_history['dew_point'])
            
            # Sort all data based on timestamps
            sorted_data = sorted(zip(timestamps, temperatures, humidities, dew_points))
            
            # Unpack sorted data back into deques
            if sorted_data:
                weather_history['timestamps'].clear()
                weather_history['temperature'].clear()
                weather_history['humidity'].clear()
                weather_history['dew_point'].clear()
                
                for t, temp, hum, dew in sorted_data:
                    weather_history['timestamps'].append(t)
                    weather_history['temperature'].append(temp)
                    weather_history['humidity'].append(hum)
                    weather_history['dew_point'].append(dew)
    except Exception as e:
        print(f"Error updating weather history: {str(e)}")

def fetch_initial_data(location):
    try:
        # Get data for the last 6 hours with 5-minute intervals
        now = datetime.now()
        start_date = (now - timedelta(hours=6)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        # First, get hourly data
        params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'dt': start_date,
            'end_dt': end_date
        }
        
        response = requests.get(WEATHER_API_HISTORY_URL, params=params)
        if response.ok:
            data = response.json()
            if 'forecast' in data and 'forecastday' in data['forecast']:
                all_hours = []
                for day in data['forecast']['forecastday']:
                    all_hours.extend(day['hour'])
                
                # Sort hours by time
                all_hours.sort(key=lambda x: datetime.strptime(x['time'], '%Y-%m-%d %H:%M'))
                
                # Process each hour
                for i in range(len(all_hours) - 1):
                    current_hour = all_hours[i]
                    next_hour = all_hours[i + 1]
                    
                    current_time = datetime.strptime(current_hour['time'], '%Y-%m-%d %H:%M')
                    next_time = datetime.strptime(next_hour['time'], '%Y-%m-%d %H:%M')
                    
                    if (now - current_time).total_seconds() <= 6 * 3600:  # Only last 6 hours
                        # Create 12 evenly spaced points between current and next hour
                        for j in range(12):
                            # Calculate the exact time for this point
                            point_time = current_time + timedelta(minutes=5*j)
                            if point_time > now:
                                break
                                
                            # Calculate progress through the hour (0 to 1)
                            progress = j / 12
                            
                            # Linear interpolation between current and next hour's values
                            temp = current_hour['temp_c'] + (next_hour['temp_c'] - current_hour['temp_c']) * progress
                            humidity = current_hour['humidity'] + (next_hour['humidity'] - current_hour['humidity']) * progress
                            
                            weather_data = {
                                'local_time': point_time.strftime('%Y-%m-%d %H:%M'),
                                'temperature_c': round(temp, 2),
                                'humidity': round(humidity)
                            }
                            update_weather_history(weather_data)
                
                # Add the most recent hour's data
                if all_hours:
                    last_hour = all_hours[-1]
                    last_time = datetime.strptime(last_hour['time'], '%Y-%m-%d %H:%M')
                    if (now - last_time).total_seconds() <= 6 * 3600:
                        weather_data = {
                            'local_time': last_hour['time'],
                            'temperature_c': last_hour['temp_c'],
                            'humidity': last_hour['humidity']
                        }
                        update_weather_history(weather_data)
            
        # Sort all data to ensure proper line connection
        timestamps = list(weather_history['timestamps'])
        temperatures = list(weather_history['temperature'])
        humidities = list(weather_history['humidity'])
        dew_points = list(weather_history['dew_point'])
        
        # Sort all data based on timestamps
        sorted_data = sorted(zip(timestamps, temperatures, humidities, dew_points))
        
        # Clear and refill with sorted data
        weather_history['timestamps'].clear()
        weather_history['temperature'].clear()
        weather_history['humidity'].clear()
        weather_history['dew_point'].clear()
        
        for t, temp, hum, dew in sorted_data:
            weather_history['timestamps'].append(t)
            weather_history['temperature'].append(temp)
            weather_history['humidity'].append(hum)
            weather_history['dew_point'].append(dew)
                
    except Exception as e:
        print(f"Error fetching initial data: {str(e)}")

def fetch_weather_data(location):
    try:
        params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'aqi': 'no'
        }
        
        response = requests.get(WEATHER_API_BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract hour from localtime for AM/PM
        hour = int(data['location']['localtime'].split(' ')[1].split(':')[0])
        is_pm = hour >= 12
        hour = hour % 12 or 12  # Convert to 12-hour format
        minute = data['location']['localtime'].split(':')[1]
        
        formatted_time = f"{hour}:{minute} {'PM' if is_pm else 'AM'}"
        
        weather_data = {
            'location': data['location']['name'],
            'region': data['location']['region'],
            'local_time': data['location']['localtime'],
            'formatted_time': formatted_time,
            'elevation': '617.0 ft',
            'coordinates': f"Lat/Lon: {data['location']['lat']}/{data['location']['lon']}",
            'temperature_c': round(data['current']['temp_c'], 2),
            'temperature_f': round(data['current']['temp_f'], 2),
            'humidity': data['current']['humidity'],
            'wind_speed': data['current']['wind_kph'],
            'wind_mph': data['current']['wind_mph'],
            'condition': data['current']['condition']['text'],
            'icon': 'https:' + data['current']['condition']['icon'],
            'feels_like_c': round(data['current']['feelslike_c'], 2),
            'feels_like_f': round(data['current']['feelslike_f'], 2),
            'wind_direction': data['current']['wind_dir'],
            'pressure_mb': data['current']['pressure_mb'],
            'visibility_km': data['current']['vis_km'],
            'uv': data['current']['uv'],
            'is_day': data['current']['is_day']
        }
        
        # Update historical data
        update_weather_history(weather_data)
        
        return weather_data
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to fetch weather data: {str(e)}'}

# Define locations with their airports
DEFAULT_LOCATION = 'Chicago'
LOCATIONS = {
    'Chicago': "Chicago Midway Airport, IL",  
    'Austin': 'Austin-Bergstrom International Airport, Austin',
    'Denver': 'Denver International Airport, Denver',
    'Philadelphia': 'Philadelphia International Airport, Philadelphia',
    'Miami': 'Miami International Airport, Miami',
    'Los Angeles': 'Los Angeles International Airport, Los Angeles',
    'New York': 'Central Park, New York'
}

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/weather/<location>')
def get_weather(location):
    if location not in LOCATIONS:
        return jsonify({'error': 'Location not found'}), 404
    
    weather_data = fetch_weather_data(LOCATIONS[location])
    return jsonify(weather_data)

@app.route('/api/weather/history/<location>')
def get_weather_history(location):
    if location not in LOCATIONS:
        return jsonify({'error': 'Location not found'}), 404
    
    # If no history exists yet, fetch initial data
    if len(weather_history['timestamps']) == 0:
        fetch_initial_data(LOCATIONS[location])
        fetch_weather_data(LOCATIONS[location])
    
    return jsonify({
        'timestamps': [t.strftime('%Y-%m-%d %H:%M') for t in weather_history['timestamps']],
        'temperature': list(weather_history['temperature']),
        'humidity': list(weather_history['humidity']),
        'dew_point': list(weather_history['dew_point'])
    })

@app.route('/api/locations')
def get_locations():
    return jsonify(list(LOCATIONS.keys()))

@app.route('/api/weather/current/<location>')
def get_current_weather(location):
    try:
        params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'aqi': 'no'
        }
        
        # Get current weather data
        response = requests.get(WEATHER_API_BASE_URL, params=params)
        if not response.ok:
            return jsonify({'error': 'Failed to fetch weather data'}), 500
            
        data = response.json()
        
        # Get forecast for today to get daily high
        forecast_params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'days': 1
        }
        forecast_url = "http://api.weatherapi.com/v1/forecast.json"
        forecast_response = requests.get(forecast_url, params=forecast_params)
        daily_high = None
        
        if forecast_response.ok:
            forecast_data = forecast_response.json()
            if 'forecast' in forecast_data and 'forecastday' in forecast_data['forecast'] and len(forecast_data['forecast']['forecastday']) > 0:
                daily_high = forecast_data['forecast']['forecastday'][0]['day']['maxtemp_c']
        
        # Calculate highest temperature in past 6 hours from our history
        six_hours_ago = datetime.now() - timedelta(hours=6)
        highest_temp_6h = None
        
        if weather_history['timestamps']:
            # Filter for last 6 hours and find max
            six_hour_temps = []
            for i, ts in enumerate(weather_history['timestamps']):
                # Check if timestamp is within the last 6 hours
                if ts >= six_hours_ago:
                    six_hour_temps.append(weather_history['temperature'][i])
            
            if six_hour_temps:
                highest_temp_6h = max(six_hour_temps)
        
        # If we don't have enough history data yet, use the current temperature as fallback
        if highest_temp_6h is None:
            highest_temp_6h = data['current']['temp_c']
            
        # Calculate dew point if not provided directly
        temperature = data['current']['temp_c']
        humidity = data['current']['humidity']
        dew_point = calculate_dew_point(temperature, humidity)
        
        # Create a complete weather data object with all required fields
        weather_data = {
            'temperature_c': temperature,
            'feels_like_c': data['current']['feelslike_c'],
            'feels_like_f': data['current']['feelslike_f'],
            'humidity': humidity,
            'dew_point_c': dew_point,
            'condition': data['current']['condition']['text'],
            'wind_kph': data['current']['wind_kph'],
            'wind_mph': data['current']['wind_mph'],
            'wind_dir': data['current']['wind_dir'],
            'pressure_mb': data['current']['pressure_mb'],
            'visibility_km': data['current']['vis_km'],
            'local_time': data['location']['localtime'],
            'location': data['location']['name'],
            'highest_temp_6h': round(highest_temp_6h, 1),
            'daily_high': round(daily_high, 1) if daily_high is not None else None
        }
        
        # Update the weather history with a simplified version of the data
        history_data = {
            'temperature_c': temperature,
            'humidity': humidity,
            'dew_point_c': dew_point,
            'local_time': data['location']['localtime']
        }
        update_weather_history(history_data)
        
        return jsonify(weather_data)
    except Exception as e:
        print(f"Error in get_current_weather: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not WEATHER_API_KEY:
        print("Warning: WEATHER_API_KEY not found in .env file")
    app.run(debug=True)
