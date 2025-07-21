from flask import Flask, render_template, request, send_file
import requests, pandas as pd
import matplotlib.pyplot as plt
import io, os, base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

VC_KEY = os.getenv("VC_API_KEY")
if not VC_KEY:
    raise RuntimeError("VC_API_KEY environment variable not set")

def fetch_vc_data(zip_code, start_date, end_date):
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{zip_code}/{start_date}/{end_date}"
        f"?unitGroup=us&elements=datetime,tempmin,temp,tempmax,humidity"
        f"&include=days&key={VC_KEY}&contentType=json"
    )
    r = requests.get(url)
    if r.status_code != 200:
        return None, None, f"API error {r.status_code}"
    j = r.json()
    days = j.get("days", [])
    if not days:
        return None, None, "No data returned"
    recs = []
    for d in days:
        recs.append({
            "date": d["datetime"],
            "temp_min": d["tempmin"],
            "temp_avg": d["temp"],
            "temp_max": d["tempmax"],
            "humidity": d["humidity"]
        })
    df = pd.DataFrame(recs)
    df["date"] = pd.to_datetime(df["date"])
    return df, j.get("address", zip_code), None

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        z = request.form["zip"].strip()
        s = request.form["start"]
        e = request.form["end"]

        # validate dates
        try:
            datetime.strptime(s, "%Y-%m-%d")
            datetime.strptime(e, "%Y-%m-%d")
        except ValueError:
            return render_template("index.html", error="Dates must be YYYY‑MM‑DD")

        df, location, err = fetch_vc_data(z, s, e)
        if err:
            return render_template("index.html", error=err)

        # CSV filename
        ts = datetime.now().strftime("%m_%d_%Y")
        filename = f"data_{z}_{ts}.csv"
        df.to_csv(filename, index=False)

        # generate plot
        buf = io.BytesIO()
        plt.figure(figsize=(10,5))
        plt.plot(df["date"], df["temp_min"], label="Min Temp",   marker="o", linestyle="-")
        plt.plot(df["date"], df["temp_avg"], label="Avg Temp",   marker="x", linestyle="--")
        plt.plot(df["date"], df["temp_max"], label="Max Temp",   marker="^", linestyle="-.")
        plt.title(f"Daily Temps in {location} ({z})")
        plt.xlabel("Date"); plt.ylabel("Temp (°F)")
        plt.xticks(rotation=45); plt.grid(True); plt.legend()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)

        img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return render_template(
            "index.html",
            img_data=img_b64,
            filename=filename,
            zip_code=z
        )

    return render_template("index.html")
    
@app.route("/download/<filename>")
def download(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return f"File {filename} not found.", 404

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
