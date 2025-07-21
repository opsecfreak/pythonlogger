from flask import Flask, render_template, request, send_file
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
from datetime import datetime, timedelta

app = Flask(__name__)

DATA_FILE = 'temperature_data.csv'

# Ensure data file exists
if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=["zip", "date", "temperature"])
    df_init.to_csv(DATA_FILE, index=False)

# Fetch historical temperature data from Open-Meteo
def fetch_temperature_data(zip_code, start_date, end_date):
    location_url = f"https://geocoding-api.open-meteo.com/v1/search?postal_code={zip_code}&country=US"
    location_res = requests.get(location_url).json()
    
    if "results" not in location_res:
        return None, None, None

    lat = location_res['results'][0]['latitude']
    lon = location_res['results'][0]['longitude']
    city = location_res['results'][0]['name']

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max&temperature_unit=fahrenheit&timezone=auto"
    )
    response = requests.get(url)
    data = response.json()

    if 'daily' not in data:
        return None, None, None

    dates = data['daily']['time']
    temps = data['daily']['temperature_2m_max']
    
    # Save to CSV
    df = pd.read_csv(DATA_FILE)
    for d, t in zip(dates, temps):
        df = df.append({"zip": zip_code, "date": d, "temperature": t}, ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

    return dates, temps, city

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        zip_code = request.form['zip']
        start = request.form['start']
        end = request.form['end']

        dates, temps, city = fetch_temperature_data(zip_code, start, end)
        if dates is None:
            return render_template('index.html', error="Could not retrieve data.")
        
        # Plot
        fig, ax = plt.subplots()
        ax.plot(dates, temps, marker='o')
        ax.set_title(f"Max Daily Temperature in {city} ({zip_code})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Temp (°F)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')

    return render_template('weatherhtml.html')

@app.route('/data.csv')
def get_csv():
    return send_file(DATA_FILE, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
