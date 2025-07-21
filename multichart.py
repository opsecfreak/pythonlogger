from flask import Flask, render_template, request, Response, send_file
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env in local/dev environments
load_dotenv()

app = Flask(__name__)

# Your Visual Crossing API key (set in env or .env)
VC_KEY = os.getenv("VC_API_KEY")
if not VC_KEY:
    raise RuntimeError("VC_API_KEY environment variable not set")

def fetch_vc_data(zip_code: str, start_date: str, end_date: str):
    """
    Fetches historical weather data for the given ZIP between start_date and end_date.
    Returns a DataFrame with columns ['date','temp_min','temp_avg','temp_max','humidity'] and the location name.
    """
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{zip_code}/{start_date}/{end_date}"
        f"?unitGroup=us"
        f"&elements=datetime,tempmin,temp,tempmax,humidity"
        f"&include=days"
        f"&key={VC_KEY}"
        f"&contentType=json"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, f"API error {resp.status_code}: {resp.text}"

    data = resp.json()
    days = data.get("days", [])
    if not days:
        return None, "No daily data returned"

    records = []
    for d in days:
        records.append({
            "date": d["datetime"],
            "temp_min": d["tempmin"],
            "temp_avg": d["temp"],
            "temp_max": d["tempmax"],
            "humidity": d["humidity"]
        })

    df = pd.DataFrame(records)
    # convert date column to datetime for plotting
    df["date"] = pd.to_datetime(df["date"])
    location = data.get("address", zip_code)
    return df, location

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        zip_code = request.form.get("zip", "").strip()
        start = request.form.get("start")
        end   = request.form.get("end")

        # Validate inputs
        for d in (start, end):
            try:
                datetime.strptime(d, "%Y-%m-%d")
            except Exception:
                return render_template("index.html", error="Dates must be YYYY‑MM‑DD")

        df, result = fetch_vc_data(zip_code, start, end)
        if df is None:
            return render_template("index.html", error=result)

        # Write CSV
        timestamp = datetime.now().strftime("%m_%d_%Y")
        filename = f"data_{zip_code}_{timestamp}.csv"
        df.to_csv(filename, index=False)

        # Create Matplotlib plot
        buf = io.BytesIO()
        plt.figure(figsize=(10, 5))
        plt.plot(df["date"], df["temp_min"], label="Min Temp (°F)",   marker="o", linestyle="-")
        plt.plot(df["date"], df["temp_avg"], label="Avg Temp (°F)",   marker="x", linestyle="--")
        plt.plot(df["date"], df["temp_max"], label="Max Temp (°F)",   marker="^", linestyle="-.")
        plt.title(f"Daily Temperatures in {result} ({zip_code})")
        plt.xlabel("Date")
        plt.ylabel("Temperature (°F)")
        plt.xticks(rotation=45)
        plt.grid(True, linestyle=":", alpha=0.7)
        plt.legend(loc="upper left")
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)

        # Return chart image, and expose CSV filename via header
        return Response(
            buf.getvalue(),
            mimetype="image/png",
            headers={"X-Csv-Filename": filename}
        )

    return render_template("index.html")

@app.route("/download/<filename>")
def download(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return f"File '{filename}' not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
