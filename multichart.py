from flask import Flask, render_template, request, Response, send_file
import requests, pandas as pd, matplotlib.pyplot as plt
import io, os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

VC_KEY = os.getenv("VC_API_KEY")

def fetch_vc_data(zip_code, start_date, end_date):
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{zip_code}/{start_date}/{end_date}"
        f"?unitGroup=us&elements=datetime,tempmax,tempmin,temp,humidity"
        f"&include=days&key={VC_KEY}&contentType=json"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, f"API Error: {resp.status_code} {resp.text}"

    j = resp.json()
    city = j.get("address", zip_code)
    days = j.get("days", [])
    if not days:
        return None, "No data returned."

    records = []
    for d in days:
        records.append({
            "date": d["datetime"],
            "temp_max": d["tempmax"],
            "temp_min": d["tempmin"],
            "temp_avg": d["temp"],
            "humidity": d["humidity"]
        })

    df = pd.DataFrame(records)
    return df, city

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        zip_code = request.form["zip"]
        start = request.form["start"]
        end = request.form["end"]

        try:
            datetime.strptime(start, "%Y-%m-%d")
            datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            return render_template("index.html", error="Invalid date format.")

        df, location_or_err = fetch_vc_data(zip_code, start, end)
        if df is None:
            return render_template("index.html", error=location_or_err)

        filename = f"data_{zip_code}_{datetime.now().strftime('%m_%d_%Y')}.csv"
        df.to_csv(filename, index=False)

        # Plot min, avg, max temps
        buf = io.BytesIO()
        plt.figure(figsize=(10, 5))
        plt.plot(df['date'], df['temp_min'], label='Min Temp', color='blue', marker='o')
        plt.plot(df['date'], df['temp_avg'], label='Avg Temp', color='green', marker='x')
        plt.plot(df['date'], df['temp_max'], label='Max Temp', color='red', marker='^')
        plt.title(f"Temperature in {location_or_err} ({zip_code})")
        plt.xlabel("Date"); plt.ylabel("Temp (°F)")
        plt.xticks(rotation=45); plt.grid(True); plt.tight_layout()
        plt.legend()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        return Response(buf.getvalue(), mimetype="image/png",
                        headers={"X-Csv-File": filename})

    return render_template("index.html")

@app.route("/download/<filename>")
def download_csv(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return f"File {filename} not found.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
