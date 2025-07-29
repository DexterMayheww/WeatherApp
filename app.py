from flask import Flask, render_template, request, flash, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import json
import time
import hashlib
import traceback

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")

# Add CORS support
CORS(app)

# Cache configuration
CACHE_DURATION = 600  # 10 minutes in seconds
weather_cache = {}

# Load cities from cities.json for search suggestion
CITIES_DATA = []
try:
    cities_file_path = os.path.join('static', 'cities.json')
    with open(cities_file_path, 'r', encoding='utf-8') as f:
        CITIES_DATA = json.load(f)
    print(f"Loaded {len(CITIES_DATA)} cities from local database")
except FileNotFoundError:
    print("Cities database not found. Using OpenWeatherMap geocoding as fallback.")
except Exception as e:
    print(f"Error loading cities database: {e}")
    CITIES_DATA = []

@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

def get_cache_key(lat, lon, units):
    """Generate a cache key for the location and units"""
    return hashlib.md5(f"{lat}_{lon}_{units}".encode()).hexdigest()

def is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    return time.time() - cache_entry['timestamp'] < CACHE_DURATION

def get_from_cache(lat, lon, units):
    """Get weather data from cache if valid"""
    cache_key = get_cache_key(lat, lon, units)
    if cache_key in weather_cache:
        cache_entry = weather_cache[cache_key]
        if is_cache_valid(cache_entry):
            return cache_entry['data']
    return None

def save_to_cache(lat, lon, units, data):
    """Save weather data to cache"""
    cache_key = get_cache_key(lat, lon, units)
    weather_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }

def cleanup_cache():
    """Remove expired cache entries"""
    current_time = time.time()
    expired_keys = [
        key for key, entry in weather_cache.items()
        if current_time - entry['timestamp'] >= CACHE_DURATION
    ]
    for key in expired_keys:
        del weather_cache[key]

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

def get_one_call_data(lat, lon, units='metric'):
    """Fetch comprehensive weather data using One Call API 3.0"""
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': units,
        'exclude': 'minutely'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            # Return error but don't crash, so fallback can be used
            return {'error': f'One Call API error: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}

def get_air_quality(lat, lon):
    """Fetch air quality data"""
    url = "http://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'Air quality API error: {response.status_code}'}
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
    
def convert_units(data, from_units, to_units):
    """Convert weather data between metric and imperial units"""
    if from_units == to_units:
        return data
    
    # Use json loads/dumps for a deep copy to prevent cache mutation
    converted_data = json.loads(json.dumps(data))
    
    if from_units == 'metric' and to_units == 'imperial':
        # Convert temperatures from Celsius to Fahrenheit
        converted_data['current']['temp'] = round((data['current']['temp'] * 9/5) + 32)
        converted_data['current']['feels_like'] = round((data['current']['feels_like'] * 9/5) + 32)
        
        # Convert wind speed from km/h to mph
        converted_data['current']['wind_speed'] = round(data['current']['wind_speed'] * 0.621371, 1)
        converted_data['current']['speed_unit'] = 'mph'
        converted_data['current']['temp_unit'] = '°F'
        
        # Convert visibility from km/h to mph
        if 'visibility' in data['current'] and data['current']['visibility'] != 'N/A':
            # Convert base unit (km) to miles
            converted_data['current']['visibility'] = round(data['current']['visibility'] * 0.621371)
        converted_data['current']['visibility_unit'] = 'miles'
        
        converted_data['current']['speed_unit'] = 'mph'
        
        # Convert hourly forecast
        for hour in converted_data.get('hourly', []):
            hour['temp'] = round((hour['temp'] * 9/5) + 32)
            hour['wind_speed'] = round(hour['wind_speed'] * 0.621371, 1)
        
        # Convert daily forecast
        for day in converted_data.get('daily', []):
            day['temp_max'] = round((day['temp_max'] * 9/5) + 32)
            day['temp_min'] = round((day['temp_min'] * 9/5) + 32)
            day['wind_speed'] = round(day['wind_speed'] * 0.621371, 1)
    
    elif from_units == 'imperial' and to_units == 'metric':
        # Convert temperatures from Fahrenheit to Celsius
        converted_data['current']['temp'] = round((data['current']['temp'] - 32) * 5/9)
        converted_data['current']['feels_like'] = round((data['current']['feels_like'] - 32) * 5/9)
        
        # Convert wind speed from mph to km/h
        converted_data['current']['wind_speed'] = round(data['current']['wind_speed'] * 1.60934, 1)
        converted_data['current']['speed_unit'] = 'km/h'
        converted_data['current']['temp_unit'] = '°C'
        
        # Convert visibility from mph to km/h
        if 'visibility' in data['current'] and data['current']['visibility'] != 'N/A':
            # Convert miles back to km
            converted_data['current']['visibility'] = round(data['current']['visibility'] / 0.621371)
        converted_data['current']['visibility_unit'] = 'km'

        converted_data['current']['speed_unit'] = 'km/h'
        
        # Convert hourly forecast
        for hour in converted_data.get('hourly', []):
            hour['temp'] = round((hour['temp'] - 32) * 5/9)
            hour['wind_speed'] = round(hour['wind_speed'] * 1.60934, 1)
        
        # Convert daily forecast
        for day in converted_data.get('daily', []):
            day['temp_max'] = round((day['temp_max'] - 32) * 5/9)
            day['temp_min'] = round((day['temp_min'] - 32) * 5/9)
            day['wind_speed'] = round(day['wind_speed'] * 1.60934, 1)
    
    return converted_data


def search_cities(query):
    """Search for cities using local database with fuzzy matching"""
    try:
        if not query or len(query) < 2:
            return []
        
        query_lower = query.lower().strip()
        matches = []
        
        # If local database is available, use it
        if CITIES_DATA and len(CITIES_DATA) > 0:
            for city in CITIES_DATA:
                try:
                    city_name = city.get('name', '').lower()
                    country = city.get('country', '').lower()
                    admin1 = city.get('adminCode', '') or city.get('admin1', '') or ''
                    
                    # Handle both 'lng' and 'lon' for longitude
                    longitude = city.get('lng') or city.get('lon')
                    latitude = city.get('lat')
                    
                    if not longitude or not latitude:
                        continue  # Skip cities without valid coordinates
                    
                    # Check if query matches the beginning of city name (prioritized)
                    if city_name.startswith(query_lower):
                        matches.append({
                            'name': city['name'],
                            'country': city['country'],
                            'state': admin1,
                            'lat': float(latitude),
                            'lon': float(longitude),  # Use the extracted longitude
                            'display': f"{city['name']}, {city['country']}" + (f" ({admin1})" if admin1 else ""),
                            'population': city.get('population', 0),
                            'priority': 1  # Highest priority for starts-with matches
                        })
                    # Check if query is contained in city name (lower priority)
                    elif query_lower in city_name:
                        matches.append({
                            'name': city['name'],
                            'country': city['country'], 
                            'state': admin1,
                            'lat': float(latitude),
                            'lon': float(longitude),  # Use the extracted longitude
                            'display': f"{city['name']}, {city['country']}" + (f" ({admin1})" if admin1 else ""),
                            'population': city.get('population', 0),
                            'priority': 2  # Lower priority for contains matches
                        })
                except (KeyError, ValueError, TypeError) as e:
                    # Skip this city if there's an issue with its data
                    print(f"Skipping city due to data error: {e}")
                    continue
            
            # Sort by priority (starts-with first), then by population (descending)
            matches.sort(key=lambda x: (x['priority'], -x.get('population', 0), x['name']))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_matches = []
            for match in matches:
                key = (match['name'], match['country'], match['lat'], match['lon'])
                if key not in seen:
                    seen.add(key)
                    # Remove the priority field before adding to results since it's only needed for sorting
                    match_copy = {k: v for k, v in match.items() if k != 'priority'}
                    unique_matches.append(match_copy)
                    if len(unique_matches) >= 10:  # Limit to top 10 results
                        break
            
            return unique_matches
        
        # Fallback to OpenWeatherMap geocoding API if local database not available
        else:
            if not API_KEY:
                print("No API key available for geocoding fallback")
                return []
                
            url = "http://api.openweathermap.org/geo/1.0/direct"
            params = {
                'q': query,
                'limit': 5,
                'appid': API_KEY
            }
            
            try:
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    api_results = response.json()
                    return [{
                        'name': city['name'],
                        'country': city['country'],
                        'state': city.get('state', ''),
                        'lat': city['lat'],
                        'lon': city['lon'],
                        'display': f"{city['name']}, {city['country']}" + (f" ({city.get('state', '')})" if city.get('state') else "")
                    } for city in api_results]
                return []
            except requests.exceptions.RequestException as e:
                print(f"Geocoding API error: {e}")
                return []
    
    except Exception as e:
        print(f"Error in search_cities: {e}")
        traceback.print_exc()
        return []

def get_uv_category(uv_index):
    """Get UV index category and recommendations"""
    if uv_index <= 2:
        return {'level': 'Low', 'color': '#289500', 'recommendation': 'No protection needed'}
    elif uv_index <= 5:
        return {'level': 'Moderate', 'color': '#F7D708', 'recommendation': 'Some protection required'}
    elif uv_index <= 7:
        return {'level': 'High', 'color': '#F85900', 'recommendation': 'Protection essential'}
    elif uv_index <= 10:
        return {'level': 'Very High', 'color': '#D8001C', 'recommendation': 'Extra protection needed'}
    else:
        return {'level': 'Extreme', 'color': '#6B49C8', 'recommendation': 'Avoid sun exposure'}

def get_aqi_category(aqi):
    """Get AQI category and color"""
    categories = {
        1: {'level': 'Good', 'color': '#00E400', 'description': 'Air quality is satisfactory'},
        2: {'level': 'Fair', 'color': '#FFFF00', 'description': 'Air quality is acceptable'},
        3: {'level': 'Moderate', 'color': '#FF7E00', 'description': 'Members of sensitive groups may experience health effects'},
        4: {'level': 'Poor', 'color': '#FF0000', 'description': 'Health effects may be experienced by everyone'},
        5: {'level': 'Very Poor', 'color': '#8F3F97', 'description': 'Health effects will be experienced by everyone'}
    }
    return categories.get(aqi, categories[1])

def get_local_time(timezone_offset):
    """Get local time for the location"""
    utc_time = datetime.utcnow()
    local_time = utc_time + timedelta(seconds=timezone_offset)
    return local_time

def format_time_with_offset(unix_timestamp, offset_seconds):
    """Converts a UTC timestamp to a formatted time string in the target timezone."""
    if not unix_timestamp or not isinstance(offset_seconds, (int, float)):
        return "N/A"
    try:
        tz = timezone(timedelta(seconds=offset_seconds))
        local_time = datetime.fromtimestamp(unix_timestamp, tz)
        return local_time.strftime('%I:%M %p')
    except (ValueError, TypeError):
        return "N/A"

@app.template_filter('timestamp_to_time')
def timestamp_to_time(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp).strftime('%I:%M %p')

@app.template_filter('timestamp_to_date')
def timestamp_to_date(unix_timestamp):
    """Convert Unix timestamp to weekday name"""
    return datetime.fromtimestamp(unix_timestamp).strftime('%a')

@app.template_filter('timestamp_to_hour')
def timestamp_to_hour(unix_timestamp):
    """Convert Unix timestamp to hour"""
    return datetime.fromtimestamp(unix_timestamp).strftime('%I %p')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/weather', methods=['POST'])
def get_weather():
    """API endpoint for getting comprehensive weather data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        city = data.get('city', '').strip()
        lat = data.get('lat')
        lon = data.get('lon')
        units = data.get('units', 'metric')
        
        if not API_KEY:
            return jsonify({'error': 'API key not configured'}), 400
        
        # Get coordinates first
        if not lat or not lon:
            if city:
                geo_data = search_cities(city)
                if not geo_data:
                    return jsonify({'error': 'City not found'}), 404
                lat = geo_data[0]['lat']
                lon = geo_data[0]['lon']
            else:
                return jsonify({'error': 'City name or coordinates required'}), 400

        # Clean up expired cache entries periodically
        cleanup_cache()
        
        # Check cache for both metric and imperial (we'll convert if needed)
        cached_data = get_from_cache(lat, lon, 'metric')
        if cached_data:
            if units == 'imperial':
                converted_data = convert_units(cached_data, 'metric', 'imperial')
                return jsonify(converted_data)
            return jsonify(cached_data)
        
        # Also check imperial cache if that's what we have
        cached_data = get_from_cache(lat, lon, 'imperial')
        if cached_data:
            if units == 'metric':
                converted_data = convert_units(cached_data, 'imperial', 'metric')
                return jsonify(converted_data)
            return jsonify(cached_data)

        try:
            # Always fetch in metric to have consistent base data
            one_call_data = get_one_call_data(lat, lon, 'metric')
            
            # --- Primary Path: One Call API Success ---
            if 'error' not in one_call_data:
                air_quality_data = get_air_quality(lat, lon)
                
                temp_unit = '°C'
                speed_unit = 'km/h'
                
                # Determine if it's day or night
                is_day = one_call_data['current']['dt'] > one_call_data['current'].get('sunrise', 0) and one_call_data['current']['dt'] < one_call_data['current'].get('sunset', 0)
                timezone_offset = one_call_data.get('timezone_offset', 0)
                
                # Use reverse geocoding to get city name if not provided
                if not city:
                    reverse_geo_url = f"http://api.openweathermap.org/geo/1.0/reverse"
                    reverse_params = {'lat': lat, 'lon': lon, 'limit': 1, 'appid': API_KEY}
                    reverse_response = requests.get(reverse_geo_url, params=reverse_params)
                    if reverse_response.status_code == 200 and reverse_response.json():
                        city = reverse_response.json()[0]['name']

                current_data = {
                    'city': city or 'Unknown Location',
                    'country': '',
                    'temp': round(one_call_data['current']['temp']),
                    'feels_like': round(one_call_data['current']['feels_like']),
                    'humidity': one_call_data['current']['humidity'],
                    'pressure': one_call_data['current']['pressure'],
                    'wind_speed': round(one_call_data['current']['wind_speed'] * 3.6, 1),  # Convert m/s to km/h
                    'description': one_call_data['current']['weather'][0]['description'].title(),
                    'icon': one_call_data['current']['weather'][0]['icon'],
                    'visibility': round(one_call_data['current'].get('visibility', 0) / 1000) if one_call_data['current'].get('visibility') is not None else 'N/A',
                    'visibility_unit': 'km',
                    'sunrise': format_time_with_offset(one_call_data['current'].get('sunrise'), timezone_offset),
                    'sunset': format_time_with_offset(one_call_data['current'].get('sunset'), timezone_offset),
                    'timezone': timezone_offset,
                    'temp_unit': temp_unit,
                    'speed_unit': speed_unit,
                    'weather_main': one_call_data['current']['weather'][0]['main'],
                    'is_day': is_day,
                    'uv_index': one_call_data['current'].get('uvi', 0),
                    'uv_info': get_uv_category(one_call_data['current'].get('uvi', 0)),
                    'local_time': get_local_time(timezone_offset).strftime('%Y-%m-%d %H:%M:%S'),
                    'lat': lat,
                    'lon': lon
                }
                
                air_quality = None
                if 'error' not in air_quality_data:
                    aqi = air_quality_data['list'][0]['main']['aqi']
                    components = air_quality_data['list'][0]['components']
                    aqi_info = get_aqi_category(aqi)
                    air_quality = {
                        'aqi': aqi, 'level': aqi_info['level'], 'color': aqi_info['color'],
                        'description': aqi_info['description'], 'components': components
                    }
                
                hourly_forecast = []
                for hour in one_call_data.get('hourly', [])[:24]:
                    hourly_forecast.append({
                        'dt': hour['dt'], 'temp': round(hour['temp']),
                        'description': hour['weather'][0]['description'].title(),
                        'icon': hour['weather'][0]['icon'], 'pop': round(hour.get('pop', 0) * 100),
                        'humidity': hour['humidity'], 'wind_speed': round(hour['wind_speed'] * 3.6, 1)  # Convert m/s to km/h
                    })
                
                daily_forecast = []
                for day in one_call_data.get('daily', [])[:7]:
                    daily_forecast.append({
                        'dt': day['dt'], 'temp_max': round(day['temp']['max']), 'temp_min': round(day['temp']['min']),
                        'description': day['weather'][0]['description'].title(), 'icon': day['weather'][0]['icon'],
                        'pop': round(day.get('pop', 0) * 100), 'humidity': day['humidity'],
                        'wind_speed': round(day['wind_speed'] * 3.6, 1), 'uvi': day.get('uvi', 0)  # Convert m/s to km/h
                    })
                
                alerts = []
                if 'alerts' in one_call_data:
                    for alert in one_call_data['alerts']:
                        alerts.append({
                            'event': alert.get('event', 'Weather Alert'), 'description': alert.get('description', ''),
                            'start': alert.get('start', 0), 'end': alert.get('end', 0), 'severity': 'moderate'
                        })
                
                response_data = {
                    'current': current_data, 'hourly': hourly_forecast, 'daily': daily_forecast,
                    'air_quality': air_quality, 'alerts': alerts
                }
                
                # Save metric data to cache
                save_to_cache(lat, lon, 'metric', response_data)
                
                # Convert to imperial if requested
                if units == 'imperial':
                    response_data = convert_units(response_data, 'metric', 'imperial')
                
                return jsonify(response_data)

            # --- Fallback Path: One Call API Failed ---
            else:
                weather_data = get_weather_by_coords(lat, lon, 'metric')
                forecast_data = get_forecast_by_coords(lat, lon, 'metric')

                if 'error' in weather_data or 'error' in forecast_data:
                    return jsonify({'error': weather_data.get('error') or forecast_data.get('error')}), 400

                temp_unit = '°C'
                speed_unit = 'km/h'
                
                is_day = weather_data['sys']['sunrise'] <= weather_data['dt'] <= weather_data['sys']['sunset']

                current_data = {
                    'city': weather_data['name'], 'country': weather_data['sys']['country'],
                    'temp': round(weather_data['main']['temp']), 'feels_like': round(weather_data['main']['feels_like']),
                    'humidity': weather_data['main']['humidity'], 'pressure': weather_data['main']['pressure'],
                    'wind_speed': round(weather_data['wind']['speed'] * 3.6, 1),  # Convert m/s to km/h
                    'description': weather_data['weather'][0]['description'].title(),
                    'icon': weather_data['weather'][0]['icon'],
                    'visibility': round(weather_data.get('visibility', 0) / 1000) if weather_data.get('visibility') is not None else 'N/A',
                    'visibility_unit': 'km',
                    'sunrise': format_time_with_offset(weather_data['sys'].get('sunrise'), weather_data['timezone']),
                    'sunset': format_time_with_offset(weather_data['sys'].get('sunset'), weather_data['timezone']),
                    'timezone': weather_data['timezone'], 'temp_unit': temp_unit, 'speed_unit': speed_unit,
                    'weather_main': weather_data['weather'][0]['main'],
                    'is_day': is_day,
                    'uv_index': 0, 'uv_info': get_uv_category(0),
                    'local_time': get_local_time(weather_data['timezone']).strftime('%Y-%m-%d %H:%M:%S'),
                    'lat': lat,
                    'lon': lon
                }

                hourly_forecast = []
                for entry in forecast_data.get('list', [])[:8]:
                    hourly_forecast.append({
                        'dt': entry['dt'], 'temp': round(entry['main']['temp']),
                        'description': entry['weather'][0]['description'].title(),
                        'icon': entry['weather'][0]['icon'], 'pop': round(entry.get('pop', 0) * 100),
                        'humidity': entry['main']['humidity'], 'wind_speed': round(entry['wind']['speed'] * 3.6, 1)  # Convert m/s to km/h
                    })

                daily_forecast = []
                processed_dates = set()
                for entry in forecast_data.get('list', []):
                    entry_date = datetime.fromtimestamp(entry['dt']).date()
                    if entry_date not in processed_dates and len(daily_forecast) < 7:
                        temps_for_day = [e['main']['temp'] for e in forecast_data['list'] if datetime.fromtimestamp(e['dt']).date() == entry_date]
                        wind_speeds_for_day = [e['wind']['speed'] for e in forecast_data['list'] if datetime.fromtimestamp(e['dt']).date() == entry_date]
                        daily_forecast.append({
                            'dt': entry['dt'], 'temp_max': round(max(temps_for_day)), 'temp_min': round(min(temps_for_day)),
                            'description': entry['weather'][0]['description'].title(),
                            'icon': entry['weather'][0]['icon'], 'pop': round(entry.get('pop', 0) * 100),
                            'humidity': entry['main']['humidity'], 'wind_speed': round(sum(wind_speeds_for_day)/len(wind_speeds_for_day) * 3.6, 1), 'uvi': 0  # Convert m/s to km/h
                        })
                        processed_dates.add(entry_date)
                
                air_quality_data = get_air_quality(lat, lon)
                air_quality = None
                if 'error' not in air_quality_data:
                    aqi = air_quality_data['list'][0]['main']['aqi']
                    aqi_info = get_aqi_category(aqi)
                    air_quality = {
                        'aqi': aqi, 'level': aqi_info['level'], 'color': aqi_info['color'],
                        'description': aqi_info['description'], 'components': air_quality_data['list'][0]['components']
                    }

                response_data = {
                    'current': current_data, 'hourly': hourly_forecast, 'daily': daily_forecast,
                    'air_quality': air_quality, 'alerts': []
                }
                
                # Save metric data to cache
                save_to_cache(lat, lon, 'metric', response_data)
                
                # Convert to imperial if requested
                if units == 'imperial':
                    response_data = convert_units(response_data, 'metric', 'imperial')
                
                return jsonify(response_data)

        except Exception as e:
            return jsonify({'error': f'Error processing weather data: {str(e)}'}), 500
    
    except Exception as e:
        print(f"Error in get_weather: {str(e)}")  # Add logging
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/search', methods=['GET'])
def search_cities_api():
    """API endpoint for city search autocomplete"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    cities = search_cities(query)
    suggestions = []
    
    for city in cities:
        state_str = f", {city.get('state', '')}" if city.get('state') else ""
        suggestion = {
            'name': city['name'], 'country': city['country'], 'state': city.get('state', ''),
            'lat': city['lat'], 'lon': city['lon'],
            'display': f"{city['name']}{state_str}, {city['country']}",
            'population': city.get('population', 0)
        }
        suggestions.append(suggestion)
        
    suggestions.sort(key=lambda x: -x.get('population', 0))
    
    return jsonify(suggestions)

@app.route('/api/geolocation', methods=['POST'])
def geolocation():
    """API endpoint for reverse geocoding"""
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    
    if not lat or not lon:
        return jsonify({'error': 'Coordinates required'}), 400
    
    url = f"http://api.openweathermap.org/geo/1.0/reverse"
    params = {'lat': lat, 'lon': lon, 'limit': 1, 'appid': API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200 and response.json():
            return jsonify(response.json()[0])
        return jsonify({'error': 'Location not found'}), 404
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Geocoding service unavailable'}), 500

@app.route('/api/compare', methods=['POST'])
def compare_weather():
    """API endpoint for comparing weather between cities"""
    data = request.get_json()
    cities = data.get('cities', [])
    units = data.get('units', 'metric')
    
    if len(cities) < 2:
        return jsonify({'error': 'At least 2 cities required for comparison'}), 400
    
    comparison_data = []
    
    for city in cities[:4]:
        # Always fetch in metric then convert
        weather_data = get_current_weather(city, 'metric')
        if 'error' not in weather_data:
            temp = round(weather_data['main']['temp'])
            feels_like = round(weather_data['main']['feels_like'])
            wind_speed = round(weather_data['wind']['speed'] * 3.6, 1)  # Convert m/s to km/h
            
            temp_unit = '°C'
            speed_unit = 'km/h'
            
            # Convert to imperial if requested
            if units == 'imperial':
                temp = round((temp * 9/5) + 32)
                feels_like = round((feels_like * 9/5) + 32)
                wind_speed = round(wind_speed * 0.621371, 1)  # Convert km/h to mph
                temp_unit = '°F'
                speed_unit = 'mph'
            
            comparison_data.append({
                'city': weather_data['name'], 'country': weather_data['sys']['country'],
                'temp': temp, 'feels_like': feels_like,
                'humidity': weather_data['main']['humidity'], 'wind_speed': wind_speed,
                'description': weather_data['weather'][0]['description'].title(),
                'icon': weather_data['weather'][0]['icon'],
                'temp_unit': temp_unit, 'speed_unit': speed_unit
            })
    
    return jsonify(comparison_data)

@app.route('/api/favorites/bulk', methods=['POST'])
def get_bulk_favorites():
    """API endpoint for getting weather data for multiple favorite cities"""
    data = request.get_json()
    favorites = data.get('favorites', [])
    units = data.get('units', 'metric')
    
    if not favorites:
        return jsonify({'error': 'No favorites provided'}), 400
    
    if not API_KEY:
        return jsonify({'error': 'API key not configured'}), 400
    
    # Clean up expired cache entries
    cleanup_cache()
    
    results = []
    cached_count = 0
    api_calls_needed = []
    
    # First, check what we have in cache
    for favorite in favorites[:10]:  # Limit to 10 favorites to avoid too many API calls
        lat = favorite.get('lat')
        lon = favorite.get('lon')
        name = favorite.get('name', 'Unknown')
        
        if not lat or not lon:
            continue
            
        # Check cache first
        cached_data = get_from_cache(lat, lon, 'metric')
        if cached_data:
            # Convert if needed and add to results
            if units == 'imperial':
                cached_data = convert_units(cached_data, 'metric', 'imperial')
            results.append({
                'name': name,
                'lat': lat,
                'lon': lon,
                'data': cached_data,
                'cached': True
            })
            cached_count += 1
        else:
            api_calls_needed.append(favorite)
    
    # Now make API calls for non-cached favorites
    for favorite in api_calls_needed:
        lat = favorite.get('lat')
        lon = favorite.get('lon')
        name = favorite.get('name', 'Unknown')
        
        try:
            # Use One Call API for comprehensive data
            one_call_data = get_one_call_data(lat, lon, 'metric')
            
            if 'error' not in one_call_data:
                # Build response data (similar to main weather endpoint but simplified)
                temp_unit = '°C'
                speed_unit = 'km/h'
                
                is_day = one_call_data['current']['dt'] > one_call_data['current'].get('sunrise', 0) and one_call_data['current']['dt'] < one_call_data['current'].get('sunset', 0)
                timezone_offset = one_call_data.get('timezone_offset', 0)
                
                current_data = {
                    'city': name,
                    'country': '',
                    'temp': round(one_call_data['current']['temp']),
                    'feels_like': round(one_call_data['current']['feels_like']),
                    'humidity': one_call_data['current']['humidity'],
                    'pressure': one_call_data['current']['pressure'],
                    'wind_speed': round(one_call_data['current']['wind_speed'] * 3.6, 1),
                    'description': one_call_data['current']['weather'][0]['description'].title(),
                    'icon': one_call_data['current']['weather'][0]['icon'],
                    'visibility': round(one_call_data['current'].get('visibility', 0) / 1000) if one_call_data['current'].get('visibility') is not None else 'N/A',
                    'visibility_unit': 'km',
                    'sunrise': format_time_with_offset(one_call_data['current'].get('sunrise'), timezone_offset),
                    'sunset': format_time_with_offset(one_call_data['current'].get('sunset'), timezone_offset),
                    'timezone': timezone_offset,
                    'temp_unit': temp_unit,
                    'speed_unit': speed_unit,
                    'weather_main': one_call_data['current']['weather'][0]['main'],
                    'is_day': is_day,
                    'uv_index': one_call_data['current'].get('uvi', 0),
                    'uv_info': get_uv_category(one_call_data['current'].get('uvi', 0)),
                    'local_time': get_local_time(timezone_offset).strftime('%Y-%m-%d %H:%M:%S'),
                    'lat': lat,
                    'lon': lon
                }
                
                # Get air quality data
                air_quality_data = get_air_quality(lat, lon)
                air_quality = None
                if 'error' not in air_quality_data:
                    aqi = air_quality_data['list'][0]['main']['aqi']
                    components = air_quality_data['list'][0]['components']
                    aqi_info = get_aqi_category(aqi)
                    air_quality = {
                        'aqi': aqi, 'level': aqi_info['level'], 'color': aqi_info['color'],
                        'description': aqi_info['description'], 'components': components
                    }
                
                # Build simplified hourly forecast (just next 6 hours for favorites)
                hourly_forecast = []
                for hour in one_call_data.get('hourly', [])[:6]:
                    hourly_forecast.append({
                        'dt': hour['dt'], 'temp': round(hour['temp']),
                        'description': hour['weather'][0]['description'].title(),
                        'icon': hour['weather'][0]['icon'], 'pop': round(hour.get('pop', 0) * 100),
                        'humidity': hour['humidity'], 'wind_speed': round(hour['wind_speed'] * 3.6, 1)
                    })
                
                # Build simplified daily forecast (just next 3 days for favorites)
                daily_forecast = []
                for day in one_call_data.get('daily', [])[:3]:
                    daily_forecast.append({
                        'dt': day['dt'], 'temp_max': round(day['temp']['max']), 'temp_min': round(day['temp']['min']),
                        'description': day['weather'][0]['description'].title(), 'icon': day['weather'][0]['icon'],
                        'pop': round(day.get('pop', 0) * 100), 'humidity': day['humidity'],
                        'wind_speed': round(day['wind_speed'] * 3.6, 1), 'uvi': day.get('uvi', 0)
                    })
                
                response_data = {
                    'current': current_data, 'hourly': hourly_forecast, 'daily': daily_forecast,
                    'air_quality': air_quality, 'alerts': []
                }
                
                # Save to cache
                save_to_cache(lat, lon, 'metric', response_data)
                
                # Convert to imperial if requested
                if units == 'imperial':
                    response_data = convert_units(response_data, 'metric', 'imperial')
                
                results.append({
                    'name': name,
                    'lat': lat,
                    'lon': lon,
                    'data': response_data,
                    'cached': False
                })
                
            else:
                # If One Call API fails, try basic current weather
                weather_data = get_weather_by_coords(lat, lon, 'metric')
                if 'error' not in weather_data:
                    forecast_data = get_forecast_by_coords(lat, lon, 'metric') # Add this line
                    
                    temp = round(weather_data['main']['temp'])
                    feels_like = round(weather_data['main']['feels_like'])
                    wind_speed = round(weather_data['wind']['speed'] * 3.6, 1)
                    
                    # Convert to imperial if requested
                    if units == 'imperial':
                        temp = round((temp * 9/5) + 32)
                        feels_like = round((feels_like * 9/5) + 32)
                        wind_speed = round(wind_speed * 0.621371, 1)
                    
                    temp_unit = '°F' if units == 'imperial' else '°C'
                    speed_unit = 'mph' if units == 'imperial' else 'km/h'
                    
                    # Fetch air quality data for the fallback
                    air_quality_data = get_air_quality(lat, lon)
                    air_quality = None
                    if 'error' not in air_quality_data:
                        aqi = air_quality_data['list'][0]['main']['aqi']
                        components = air_quality_data['list'][0]['components']
                        aqi_info = get_aqi_category(aqi)
                        air_quality = {
                            'aqi': aqi, 'level': aqi_info['level'], 'color': aqi_info['color'],
                            'description': aqi_info['description'], 'components': components
                        }
                    
                    # Build simplified hourly forecast from fallback data
                    hourly_forecast = []
                    if 'error' not in forecast_data:
                        for entry in forecast_data.get('list', [])[:8]: # Next 6 hours
                            hourly_forecast.append({
                                'dt': entry['dt'], 'temp': round(entry['main']['temp']),
                                'description': entry['weather'][0]['description'].title(),
                                'icon': entry['weather'][0]['icon'], 'pop': round(entry.get('pop', 0) * 100),
                                'humidity': entry['main']['humidity'], 'wind_speed': round(entry['wind']['speed'] * 3.6, 1)
                            })
                    
                    # Build simplified daily forecast from fallback data
                    daily_forecast = []
                    if 'error' not in forecast_data:
                        processed_dates = set()
                        for entry in forecast_data.get('list', []):
                            entry_date = datetime.fromtimestamp(entry['dt']).date()
                            if entry_date not in processed_dates and len(daily_forecast) < 5: # Next 3 days
                                temps_for_day = [e['main']['temp'] for e in forecast_data['list'] if datetime.fromtimestamp(e['dt']).date() == entry_date]
                                wind_speeds_for_day = [e['wind']['speed'] for e in forecast_data['list'] if datetime.fromtimestamp(e['dt']).date() == entry_date]
                                daily_forecast.append({
                                    'dt': entry['dt'], 'temp_max': round(max(temps_for_day)), 'temp_min': round(min(temps_for_day)),
                                    'description': entry['weather'][0]['description'].title(),
                                    'icon': entry['weather'][0]['icon'], 'pop': round(entry.get('pop', 0) * 100),
                                    'humidity': entry['main']['humidity'], 'wind_speed': round(sum(wind_speeds_for_day)/len(wind_speeds_for_day) * 3.6, 1), 'uvi': 0
                                })
                                processed_dates.add(entry_date)
                    
                    timezone_offset = weather_data.get('timezone', 0)
                    is_day = weather_data['dt'] > weather_data['sys'].get('sunrise', 0) and weather_data['dt'] < weather_data['sys'].get('sunset', 0)
                    
                    # Simplified data for failed One Call API
                    simplified_data = {
                        'current': {
                            'city': name,
                            'country': weather_data['sys']['country'],
                            'temp': temp,
                            'feels_like': feels_like,
                            'humidity': weather_data['main']['humidity'],
                            'pressure': weather_data['main']['pressure'],
                            'wind_speed': wind_speed,
                            'description': weather_data['weather'][0]['description'].title(),
                            'icon': weather_data['weather'][0]['icon'],
                            'visibility': round(weather_data.get('visibility', 0) / 1000) if weather_data.get('visibility') is not None else 'N/A',
                            'visibility_unit': 'km',
                            'sunrise': format_time_with_offset(weather_data['sys'].get('sunrise'), weather_data.get('timezone', 0)),
                            'sunset': format_time_with_offset(weather_data['sys'].get('sunset'), weather_data.get('timezone', 0)),
                            'timezone': weather_data.get('timezone', 0),
                            'local_time': get_local_time(weather_data.get('timezone', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                            'temp_unit': temp_unit,
                            'speed_unit': speed_unit,
                            'weather_main': weather_data['weather'][0]['main'],
                            'lat': lat,
                            'lon': lon,
                            'is_day': is_day,
                            'uv_index': 0,
                            'uv_info': get_uv_category(0)
                        },
                        'hourly': hourly_forecast,
                        'daily': daily_forecast,
                        'air_quality': air_quality,
                        'alerts': []
                    }
                    
                    results.append({
                        'name': name,
                        'lat': lat,
                        'lon': lon,
                        'data': simplified_data,
                        'cached': False
                    })
        
        except Exception as e:
            # Log error but continue with other favorites
            print(f"Error fetching weather for {name}: {str(e)}")
            continue
    
    return jsonify({
        'results': results,
        'cached_count': cached_count,
        'total_count': len(results),
        'api_calls_made': len(api_calls_needed) - (len(api_calls_needed) - len([r for r in results if not r.get('cached', True)]))
    })

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