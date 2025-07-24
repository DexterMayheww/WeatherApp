from flask import Flask, render_template, request, flash, jsonify
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")

def get_current_weather(city, units='metric'):
    """Fetch current weather data for a city"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': API_KEY,
        'units': units
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {'error': 'City not found'}
        else:
            return {'error': f'Weather service error: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}

def get_weather_by_coords(lat, lon, units='metric'):
    """Fetch weather data by coordinates"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': units
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'Weather service error: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}

def get_forecast(city, units='metric'):
    """Fetch 5-day forecast data for a city"""
    url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        'q': city,
        'appid': API_KEY,
        'units': units
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {'error': 'City not found'}
        else:
            return {'error': f'Forecast service error: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}

def get_forecast_by_coords(lat, lon, units='metric'):
    """Fetch forecast data by coordinates"""
    url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': units
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'Forecast service error: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}

def search_cities(query):
    """Search for cities using geocoding API"""
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        'q': query,
        'limit': 5,
        'appid': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.exceptions.RequestException:
        return []

def get_weather_background(weather_condition, is_day=True):
    """Get background gradient based on weather condition"""
    backgrounds = {
        'clear': {
            'day': 'linear-gradient(135deg, #87CEEB 0%, #98D8E8 50%, #B6E5F7 100%)',
            'night': 'linear-gradient(135deg, #2C3E50 0%, #34495E 50%, #4A6741 100%)'
        },
        'clouds': {
            'day': 'linear-gradient(135deg, #BDC3C7 0%, #95A5A6 50%, #7F8C8D 100%)',
            'night': 'linear-gradient(135deg, #34495E 0%, #2C3E50 50%, #1B2631 100%)'
        },
        'rain': {
            'day': 'linear-gradient(135deg, #4A90E2 0%, #5DADE2 50%, #85C1E9 100%)',
            'night': 'linear-gradient(135deg, #1B4F72 0%, #2E86AB 50%, #A8E6CF 100%)'
        },
        'snow': {
            'day': 'linear-gradient(135deg, #E8F8F5 0%, #D5DBDB 50%, #AEB6BF 100%)',
            'night': 'linear-gradient(135deg, #5D6D7E 0%, #85929E 50%, #D5DBDB 100%)'
        },
        'thunderstorm': {
            'day': 'linear-gradient(135deg, #566573 0%, #34495E 50%, #2C3E50 100%)',
            'night': 'linear-gradient(135deg, #1B2631 0%, #283747 50%, #34495E 100%)'
        },
        'mist': {
            'day': 'linear-gradient(135deg, #D5DBDB 0%, #AEB6BF 50%, #85929E 100%)',
            'night': 'linear-gradient(135deg, #566573 0%, #34495E 50%, #2C3E50 100%)'
        }
    }
    
    condition_key = weather_condition.lower()
    for key in backgrounds:
        if key in condition_key:
            return backgrounds[key]['day' if is_day else 'night']
    
    return backgrounds['clear']['day' if is_day else 'night']

def create_mock_alerts(weather_condition, temp, wind_speed, units, temp_unit):
    """Create mock weather alerts based on the provided unit system."""
    alerts = []
    
    # Define thresholds for both metric and imperial systems
    heat_threshold = 35 if units == 'metric' else 95  # 35°C ~ 95°F
    cold_threshold = -10 if units == 'metric' else 14 # -10°C ~ 14°F
    wind_threshold = 15 if units == 'metric' else 33.5 # 15 m/s ~ 33.5 mph

    # Temperature alerts
    if temp > heat_threshold:
        alerts.append({
            'event': 'Heat Warning',
            'description': f'High temperature of {round(temp)}{temp_unit} expected. Stay hydrated and avoid prolonged sun exposure.',
            'severity': 'moderate',
            'start': datetime.now().isoformat(),
            'end': (datetime.now() + timedelta(hours=6)).isoformat()
        })
    elif temp < cold_threshold:
        alerts.append({
            'event': 'Cold Weather Advisory',
            'description': f'Very low temperature of {round(temp)}{temp_unit}. Dress warmly and be aware of frostbite risk.',
            'severity': 'moderate',
            'start': datetime.now().isoformat(),
            'end': (datetime.now() + timedelta(hours=12)).isoformat()
        })
    
    # Wind alerts
    if wind_speed > wind_threshold:
        if units == 'metric':
            display_speed = round(wind_speed * 3.6)
            speed_unit = 'km/h'
        else:
            display_speed = round(wind_speed)
            speed_unit = 'mph'
            
        alerts.append({
            'event': 'High Wind Advisory',
            'description': f'Strong winds of {display_speed} {speed_unit} expected. Secure loose objects.',
            'severity': 'minor',
            'start': datetime.now().isoformat(),
            'end': (datetime.now() + timedelta(hours=8)).isoformat()
        })
    
    # Weather condition alerts
    if 'thunderstorm' in weather_condition.lower():
        alerts.append({
            'event': 'Thunderstorm Warning',
            'description': 'Thunderstorm conditions expected. Stay indoors and avoid outdoor activities.',
            'severity': 'moderate',
            'start': datetime.now().isoformat(),
            'end': (datetime.now() + timedelta(hours=4)).isoformat()
        })
    
    return alerts

@app.template_filter('timestamp_to_time')
def timestamp_to_time(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp).strftime('%I:%M %p')

@app.template_filter('timestamp_to_date')
def timestamp_to_date(unix_timestamp):
    """Convert Unix timestamp to weekday name"""
    return datetime.fromtimestamp(unix_timestamp).strftime('%a')

@app.template_filter('timestamp_to_full_date')
def timestamp_to_full_date(unix_timestamp):
    """Convert Unix timestamp to full date"""
    return datetime.fromtimestamp(unix_timestamp).strftime('%B %d, %Y')

@app.template_filter('timestamp_to_hour')
def timestamp_to_hour(unix_timestamp):
    """Convert Unix timestamp to hour"""
    return datetime.fromtimestamp(unix_timestamp).strftime('%I %p')

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/api/weather', methods=['POST'])
def get_weather():
    """API endpoint for getting weather data"""
    data = request.get_json()
    city = data.get('city', '').strip()
    lat = data.get('lat')
    lon = data.get('lon')
    units = data.get('units', 'metric')
    
    if not API_KEY:
        return jsonify({'error': 'API key not configured'}), 400
    
    # Get weather data
    if lat and lon:
        weather_data = get_weather_by_coords(lat, lon, units)
        forecast_data = get_forecast_by_coords(lat, lon, units)
    elif city:
        weather_data = get_current_weather(city, units)
        forecast_data = get_forecast(city, units)
    else:
        return jsonify({'error': 'City name or coordinates required'}), 400
    
    if 'error' in weather_data:
        return jsonify({'error': weather_data['error']}), 400
    
    try:
        # Process current weather
        temp_unit = '°F' if units == 'imperial' else '°C'
        if units == 'metric':
            speed_unit = 'km/h'
            # Conversion factor from m/s to km/h is 3.6
            wind_speed_conversion_factor = 3.6
        else:
            speed_unit = 'mph'
            wind_speed_conversion_factor = 1
        
        # Determine if it's day or night
        current_time = datetime.now().timestamp()
        is_day = weather_data['sys']['sunrise'] <= current_time <= weather_data['sys']['sunset']
        
        current_data = {
            'city': weather_data['name'],
            'country': weather_data['sys']['country'],
            'temp': round(weather_data['main']['temp']),
            'feels_like': round(weather_data['main']['feels_like']),
            'humidity': weather_data['main']['humidity'],
            'pressure': weather_data['main']['pressure'],
            'wind_speed': round(weather_data['wind']['speed'] * wind_speed_conversion_factor, 1),
            'wind_deg': weather_data['wind'].get('deg', 0),
            'description': weather_data['weather'][0]['description'].title(),
            'icon': weather_data['weather'][0]['icon'],
            'visibility': weather_data.get('visibility', 'N/A'),
            'sunrise': weather_data['sys']['sunrise'],
            'sunset': weather_data['sys']['sunset'],
            'timezone': weather_data['timezone'],
            'temp_unit': temp_unit,
            'speed_unit': speed_unit,
            'background': get_weather_background(weather_data['weather'][0]['main'], is_day)
        }
        
        # Create mock alerts with correct unit context
        alerts = create_mock_alerts(
            weather_data['weather'][0]['main'],
            weather_data['main']['temp'],
            weather_data['wind']['speed'],
            units,
            temp_unit
        )
        
        # Process hourly forecast (next 24 hours from 5-day forecast)
        hourly_forecast = []
        daily_forecast = []
        
        if 'error' not in forecast_data and 'list' in forecast_data:
            # Hourly forecast - take first 8 entries (24 hours)
            for i, entry in enumerate(forecast_data['list'][:8]):
                hourly_forecast.append({
                    'dt': entry['dt'],
                    'temp': round(entry['main']['temp']),
                    'description': entry['weather'][0]['description'].title(),
                    'icon': entry['weather'][0]['icon'],
                    'humidity': entry['main']['humidity'],
                    'wind_speed': round(weather_data['wind']['speed'] * wind_speed_conversion_factor, 1),
                    'pop': round(entry.get('pop', 0) * 100)  # Probability of precipitation
                })
            
            # Daily forecast - one entry per day around noon
            processed_dates = set()
            for entry in forecast_data['list']:
                entry_date = datetime.fromtimestamp(entry['dt']).date()
                entry_hour = datetime.fromtimestamp(entry['dt']).hour
                
                if entry_date not in processed_dates and 10 <= entry_hour <= 14:
                    daily_forecast.append({
                        'dt': entry['dt'],
                        'temp_max': round(entry['main']['temp_max']),
                        'temp_min': round(entry['main']['temp_min']),
                        'temp': round(entry['main']['temp']),
                        'description': entry['weather'][0]['description'].title(),
                        'icon': entry['weather'][0]['icon'],
                        'humidity': entry['main']['humidity'],
                        'wind_speed': round(entry['wind']['speed'], 1),
                        'pop': round(entry.get('pop', 0) * 100)
                    })
                    processed_dates.add(entry_date)
                    
                    if len(daily_forecast) >= 5:
                        break
        
        return jsonify({
            'current': current_data,
            'hourly': hourly_forecast,
            'daily': daily_forecast,
            'alerts': alerts
        })
        
    except KeyError as e:
        return jsonify({'error': f'Error parsing weather data: {str(e)}'}), 500

@app.route('/api/search', methods=['GET'])
def search_cities_api():
    """API endpoint for city search autocomplete"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    cities = search_cities(query)
    suggestions = []
    
    for city in cities:
        suggestion = {
            'name': city['name'],
            'country': city['country'],
            'state': city.get('state', ''),
            'lat': city['lat'],
            'lon': city['lon'],
            'display': f"{city['name']}, {city.get('state', '')}, {city['country']}".replace(', ,', ',')
        }
        suggestions.append(suggestion)
    
    return jsonify(suggestions)

@app.route('/api/geolocation', methods=['POST'])
def geolocation():
    """API endpoint for reverse geocoding"""
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    
    if not lat or not lon:
        return jsonify({'error': 'Coordinates required'}), 400
    
    # Reverse geocode to get city name
    url = f"http://api.openweathermap.org/geo/1.0/reverse"
    params = {
        'lat': lat,
        'lon': lon,
        'limit': 1,
        'appid': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            geo_data = response.json()
            if geo_data:
                city_data = geo_data[0]
                return jsonify({
                    'city': city_data['name'],
                    'country': city_data['country'],
                    'state': city_data.get('state', ''),
                    'lat': lat,
                    'lon': lon
                })
        return jsonify({'error': 'Location not found'}), 404
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Geocoding service unavailable'}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    if not API_KEY:
        print("Warning: OPENWEATHER_API_KEY not found in environment variables")
    app.run(debug=True, host='0.0.0.0', port=5000)