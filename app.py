from flask import Flask, render_template, request, redirect, url_for, flash
import requests
import time
from datetime import datetime, timedelta
from statistics import mean
import math  

app = Flask(__name__)
app.secret_key = 'supersecretkey'


cloudThresh = 20

# distance
def earthDistance(lat1, lon1, lat2, lon2):
    
 
    
    R = 3958.8  
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# weather city
def get_weather(city):
    
   
   
    API_KEY = "5339a8daf0e4fc156c88434221e73842"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=imperial"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code != 200 or data.get("cod") != 200:
        raise ValueError(f"City '{city}' could not be found. {data.get('message', '')}")
    
    clouds = data['clouds']['all']
    currentTime = data['dt']
    sunset = data['sys']['sunset']
    sunrise = data['sys']['sunrise']
    citylon = data['coord']['lon']
    citylat = data['coord']['lat']
    night = 1 if (currentTime < sunrise or currentTime > sunset) else 0
    return clouds, night, citylon, citylat

#weather coordinates
def get_weather_by_coords(lat, lon):
    
   
    
    API_KEY = "5339a8daf0e4fc156c88434221e73842"
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code != 200 or data.get("cod") != 200:
        raise ValueError(f"Weather data could not be fetched for coordinates ({lat}, {lon}). {data.get('message', '')}")
    
    clouds = data['clouds']['all']
    currentTime = data['dt']
    sunset = data['sys']['sunset']
    sunrise = data['sys']['sunrise']
    citylon = data['coord']['lon']
    citylat = data['coord']['lat']
    night = 1 if (currentTime < sunrise or currentTime > sunset) else 0
    return clouds, night, citylon, citylat

# ISS pos
def get_ISS_data():
    url = "http://api.open-notify.org/iss-now.json"
    response = requests.get(url)
    data = response.json()
    issLatitude = float(data['iss_position']['latitude'])
    issLongitude = float(data['iss_position']['longitude'])
    return issLongitude, issLatitude

#check within five degrees
def is_iss_overhead(iss_lat, iss_lon, user_lon, user_lat):
    
    
    
    degree = 5
    return abs(iss_lat - user_lat) <= degree and abs(iss_lon - user_lon) <= degree

# Kp Index
BASE_URL_KP = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'

def fetch_geomagnetic_data():
    try:
        response = requests.get(BASE_URL_KP)
        response.raise_for_status()
        return response.json() 
    except requests.exceptions.RequestException as e:
        print(f"Error fetching geomagnetic data: {e}")
        return None

def filter_and_analyze_geomagnetic_data(data, days=7):
    if not data:
        return [], {}
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_data = []
    for entry in data:
        entry_time = datetime.fromisoformat(entry['time_tag'].replace('Z', '+00:00'))
        if entry_time > cutoff_date:
            filtered_data.append(entry)
    if not filtered_data:
        return [], {}
    kp_values = [entry['kp_index'] for entry in filtered_data]
    estimated_kp_values = [entry['estimated_kp'] for entry in filtered_data]
    daily_stats = {}
    for entry in filtered_data:
        day = entry['time_tag'][:10]
        if day not in daily_stats:
            daily_stats[day] = {'kp_values': [], 'estimated_kp_values': []}
        daily_stats[day]['kp_values'].append(entry['kp_index'])
        daily_stats[day]['estimated_kp_values'].append(entry['estimated_kp'])
    summary = {
        'time_range': {
            'start': filtered_data[0]['time_tag'],
            'end': filtered_data[-1]['time_tag']
        },
        'overall_stats': {
            'max_kp': max(kp_values),
            'min_kp': min(kp_values),
            'avg_kp': round(mean(kp_values), 2),
            'max_estimated_kp': round(max(estimated_kp_values), 2),
            'min_estimated_kp': round(min(estimated_kp_values), 2),
            'avg_estimated_kp': round(mean(estimated_kp_values), 2)
        },
        'daily_stats': {
            day: {
                'avg_kp': round(mean(stats['kp_values']), 2),
                'avg_estimated_kp': round(mean(stats['estimated_kp_values']), 2),
                'max_kp': max(stats['kp_values']),
                'max_estimated_kp': round(max(stats['estimated_kp_values']), 2)
            }
            for day, stats in daily_stats.items()
        }
    }
    return filtered_data, summary


BASE_URL_FLUX = 'https://services.swpc.noaa.gov/json/f107_cm_flux.json'

#flux
def fetch_solar_flux_data():
    try:
        response = requests.get(BASE_URL_FLUX)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching solar flux data: {e}")
        return None
def filter_and_analyze_flux_data(data, days=7):
    if not data:
        return [], {}
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_data = []
    for entry in data:
        entry_time = datetime.fromisoformat(entry['time_tag'].replace('Z', '+00:00'))
        if entry_time > cutoff_date:
            filtered_data.append(entry)
    if not filtered_data:
        return [], {}
    flux_values = [entry['flux'] for entry in filtered_data]
    daily_stats = {}
    for entry in filtered_data:
        day = entry['time_tag'][:10]
        if day not in daily_stats:
            daily_stats[day] = {'flux_values': []}
        daily_stats[day]['flux_values'].append(entry['flux'])
    summary = {
        'time_range': {
            'start': filtered_data[0]['time_tag'],
            'end': filtered_data[-1]['time_tag']
        },
        'overall_stats': {
            'max_flux': max(flux_values),
            'min_flux': min(flux_values),
            'avg_flux': round(mean(flux_values), 2)
        },
        'daily_stats': {
            day: {
                'avg_flux': round(mean(stats['flux_values']), 2),
                'max_flux': max(stats['flux_values'])
            }
            for day, stats in daily_stats.items()
        }
    }
    return filtered_data, summary


# FLASK ROUTE

@app.route('/', methods=['GET', 'POST'])
def index():
    context = {}
    if request.method == 'POST':
       
        submit_type = request.form.get("submitType")
        try:
            if submit_type == "manual":
                
                city = request.form.get("city")
                if not city:
                    flash("Please enter a city.")
                    return redirect(url_for('index'))
                clouds, night, loc_lon, loc_lat = get_weather(city)
            elif submit_type == "geo":
                
                user_lat = request.form.get("lat")
                user_lon = request.form.get("lon")
                if not user_lat or not user_lon:
                    flash("Please allow location access or manually enter a city.")
                    return redirect(url_for('index'))
                user_lat = float(user_lat)
                user_lon = float(user_lon)
                clouds, night, loc_lon, loc_lat = get_weather_by_coords(user_lat, user_lon)
                city = ""  
            else:
                flash("Unknown submission type.")
                return redirect(url_for('index'))
        except Exception as e:
            flash(str(e))
            return redirect(url_for('index'))
        
        issLongitude, issLatitude = get_ISS_data()
        iss_overhead = is_iss_overhead(issLatitude, issLongitude, loc_lon, loc_lat)
        weatherClear = (night == 1) and (clouds < cloudThresh)
        
        if iss_overhead and weatherClear:
            message = "Good news! The ISS is overhead and the sky is clear. You can see the ISS!"
        elif night == 0:
            if iss_overhead:
                message = "It is currently daytime so you probably can't see the ISS, but it is up there."
            else:
                message = "It is day so you couldn't see the ISS even if it was there, sadly it is not."
        elif clouds >= cloudThresh:
            if iss_overhead:
                message = "It's too cloudy to see the ISS, but it is overhead."
            else:
                message = "It is too cloudy to see the ISS, but that's ok because it's not overhead."
        else:
            message = "The ISS is not overhead at the moment and it is too light and cloudy to see it anyways."
        
        
        distance = earthDistance(loc_lat, loc_lon, issLatitude, issLongitude)
        distance = round(distance, 2)
        
        context.update({
            "message": message,
            "clouds": clouds,
            "night": night,
            "iss_lat": issLatitude,
            "iss_lon": issLongitude,
            "iss_overhead": iss_overhead,
            "citylat": loc_lat,
            "citylon": loc_lon,
            "distance": distance,
            "city": city
        })
    
    
    geomagnetic_data = fetch_geomagnetic_data()
    _, geomagnetic_summary = filter_and_analyze_geomagnetic_data(geomagnetic_data)
    solar_flux_data = fetch_solar_flux_data()
    _, flux_summary = filter_and_analyze_flux_data(solar_flux_data)
    
    context.update({
        "geomagnetic_summary": geomagnetic_summary,
        "flux_summary": flux_summary
    })
    
    return render_template("index.html", **context)

if __name__ == '__main__':
    app.run(debug=True)
