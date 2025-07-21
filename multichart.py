from flask import Flask, render_template, request, Response, send_file
import requests, pandas as pd, matplotlib.pyplot as plt
import io, os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Load VC_API_KEY from .env if running locally

app = Flask(__name__)
VC_KEY = os.getenv("VC_API_KEY")

def fetch_vc_data(zip_code, start_date, end_date):
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{zip_code}/{start_date}/{end_date}"
        f"?unitGroup=us&elements=datetime,tempmax&include=days&key={VC_KEY}&contentType=json"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, None, None, f"API error: {resp.status_code}"

    j = resp.json()
    city = j.get("address", zip_code)
    days = j.get("days", [])
    if not days:
        return None, None, None, "No data available"

    dates = [d["datetime"] for d in days]
    temps = [d["tempmax"] for d in days]

    return dates, temps, city, None

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

        dates, temps, city, error = fetch_vc_data(zip_code, start, end)
        if error:
            return render_template("index.html", error=error)

        # Save data to ZIP_MM_DD_YYYY.csv
        filename = f"data_{zip_code}_{datetime.now().strftime('%m_%d_%Y')}.csv"
        df = pd.DataFrame({"date": dates, "temp_max": temps})
        df.to_csv(filename, index=False)

        # Plot
        buf = io.BytesIO()
        plt.figure(figsize=(10, 5))
        plt.plot(dates, temps, marker='o', color='orange', linestyle='-')
        plt.title(f"Max Temp in {city} ({zip_code})")
        plt.xlabel("Date"); plt.ylabel("Temperature (°F)")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        # Store CSV file path in session-less way
        return Response(buf.getvalue(), mimetype="image/png",
                        headers={"X-Csv-File": filename})

    return render_template("index.html")

@app.route("/download/<zip>/<filename>")
def download(zip, filename):
    return send_file(f"data_{zip}_{filename}", as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
