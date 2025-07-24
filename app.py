from flask import Flask, render_template, request, flash, jsonify
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")  # For flash messages

def get_current_weather(city):
    """Fetch current weather data for a city"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': API_KEY,
        'units': 'metric'
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

def get_forecast(city):
    """Fetch 5-day forecast data for a city"""
    url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        'q': city,
        'appid': API_KEY,
        'units': 'metric'
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

@app.route('/', methods=['GET', 'POST'])
def index():
    data = None
    forecast = None
    city = ""
    error_message = None

    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        
        if not city:
            flash('Please enter a city name', 'error')
            return render_template('index.html', data=data, forecast=forecast, city=city)
        
        if not API_KEY:
            flash('API key not configured. Please check your environment variables.', 'error')
            return render_template('index.html', data=data, forecast=forecast, city=city)

        # Get current weather
        weather_data = get_current_weather(city)
        
        if 'error' in weather_data:
            flash(weather_data['error'], 'error')
        else:
            try:
                data = {
                    'city': weather_data['name'],
                    'country': weather_data['sys']['country'],
                    'temp': round(weather_data['main']['temp']),
                    'feels_like': round(weather_data['main']['feels_like']),
                    'humidity': weather_data['main']['humidity'],
                    'pressure': weather_data['main']['pressure'],
                    'wind_speed': round(weather_data['wind']['speed'], 1),
                    'wind_deg': weather_data['wind'].get('deg', 0),
                    'description': weather_data['weather'][0]['description'].title(),
                    'icon': weather_data['weather'][0]['icon'],
                    'visibility': weather_data.get('visibility', 'N/A'),
                    'sunrise': weather_data['sys']['sunrise'],
                    'sunset': weather_data['sys']['sunset'],
                    'timezone': weather_data['timezone']
                }
            except KeyError as e:
                flash(f'Error parsing weather data: {str(e)}', 'error')

        # Get 5-day forecast if current weather was successful
        if data:
            forecast_data = get_forecast(city)
            
            if 'error' not in forecast_data:
                try:
                    forecast = []
                    # Process forecast data - take one entry per day (around noon)
                    processed_dates = set()
                    
                    for entry in forecast_data['list']:
                        entry_date = datetime.fromtimestamp(entry['dt']).date()
                        entry_hour = datetime.fromtimestamp(entry['dt']).hour
                        
                        # Take the forecast closest to noon for each day
                        if entry_date not in processed_dates and 10 <= entry_hour <= 14:
                            day = {
                                'dt': entry['dt'],
                                'temp_max': round(entry['main']['temp_max']),
                                'temp_min': round(entry['main']['temp_min']),
                                'temp': round(entry['main']['temp']),
                                'description': entry['weather'][0]['description'].title(),
                                'icon': entry['weather'][0]['icon'],
                                'humidity': entry['main']['humidity'],
                                'wind_speed': round(entry['wind']['speed'], 1)
                            }
                            forecast.append(day)
                            processed_dates.add(entry_date)
                            
                            # Limit to 5 days
                            if len(forecast) >= 5:
                                break
                                
                except KeyError as e:
                    flash(f'Error parsing forecast data: {str(e)}', 'error')

    return render_template('index.html', data=data, forecast=forecast, city=city)

@app.route('/geolocation', methods=['POST'])
def geolocation():
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    
    # Reverse geocode to get city name
    url = f"http://api.openweathermap.org/geo/1.0/reverse"
    params = {
        'lat': lat,
        'lon': lon,
        'limit': 1,
        'appid': API_KEY
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        geo_data = response.json()
        if geo_data:
            city_name = geo_data[0]['name']
            return jsonify({'city': city_name})
    
    return jsonify({'city': None})

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