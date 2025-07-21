from flask import Flask, render_template, request, Response, send_file
import requests, pandas as pd, matplotlib.pyplot as plt
import io, os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
# weatherapi_app.py
app = Flask(__name__)
DATA_FILE = 'temperature_data.csv'
VC_KEY = os.getenv("VC_API_KEY")  # set this in Codespaces secrets

# Ensure CSV exists
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=["zip","date","temp_max"]).to_csv(DATA_FILE, index=False)

def fetch_vc_data(zip_code, start_date, end_date):
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{zip_code}/{start_date}/{end_date}"
        f"?unitGroup=us&elements=datetime,tempmax&include=days&key={VC_KEY}&contentType=json"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, None, resp.text

    j = resp.json()
    city = j.get("address", zip_code)
    days = j.get("days", [])
    dates = [d["datetime"] for d in days]
    temps = [d["tempmax"] for d in days]

    # Save to CSV
    df = pd.read_csv(DATA_FILE)
    new = pd.DataFrame({"zip":zip_code,"date":dates,"temp_max":temps})
    df = pd.concat([df, new]).drop_duplicates(subset=["zip","date"], keep="last")
    df.to_csv(DATA_FILE, index=False)

    return dates, temps, city

@app.route("/", methods=["GET","POST"])
def index():
    if request.method=="POST":
        z = request.form["zip"]
        s = request.form["start"]
        e = request.form["end"]
        dates, temps, location_or_err = fetch_vc_data(z, s, e)
        if dates is None:
            return render_template("index.html", error=f"Error: {location_or_err}")
        buf = io.BytesIO()
        plt.figure(figsize=(8,4))
        plt.plot(dates, temps, marker="o")
        plt.title(f"Max Daily Temp for {location_or_err}")
        plt.xlabel("Date"); plt.ylabel("Temp (°F)")
        plt.xticks(rotation=45); plt.tight_layout()
        plt.savefig(buf, format="png"); plt.close()
        buf.seek(0)
        return Response(buf.getvalue(), mimetype="image/png")
    return render_template("weatherhtml.html")

@app.route("/data.csv")
def download_csv():
    return send_file(DATA_FILE, as_attachment=True)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
