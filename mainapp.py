from flask import Flask, render_template, Response
import matplotlib.pyplot as plt
import io
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Generate dummy user data for 30 days
def generate_user_data():
    base_date = datetime.now()
    dates = [(base_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    user_counts = [random.randint(50, 200) for _ in range(30)]
    return dates, user_counts

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/plot.png')
def plot_png():
    dates, user_counts = generate_user_data()
    fig, ax = plt.subplots()
    ax.plot(dates, user_counts, marker='o', color='blue', linestyle='-')
    ax.set_title('User Growth Over 30 Days')
    ax.set_xlabel('Date')
    ax.set_ylabel('Users')
    ax.tick_params(axis='x', rotation=45)
    fig.tight_layout()

    # Convert to PNG image
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
