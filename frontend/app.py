from flask import Flask, render_template
from config import settings  # Import the settings instance from config.py

app = Flask(__name__)

@app.route("/")
def index():
    # Pass the API key to the template
    return render_template("index.html", google_maps_api_key=settings.google_maps_api_key)

if __name__ == '__main__':
    app.run(debug=True)
