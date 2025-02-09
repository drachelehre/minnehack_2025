from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import settings
import googlemaps, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from utils.fetch_data import get_nearby_businesses
from utils.radius_calc import find_radius

import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with a strong secret key.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mhdatabase2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and login manager.
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize the Google Maps client.
gmaps = googlemaps.Client(key=settings.google_maps_api_key)

# ----------------------------
# Database Model for Users
# ----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    home_address = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    cummulative_reward = db.Column(db.Float, default=0)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def calculate_rewards(self):
        transactions = Transaction.query.filter_by(user_id=self.id).all()
        total_rewards = sum([transaction.amount for transaction in transactions])
        self.cummulative_reward = total_rewards
        

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    business_type = db.Column(db.String(100))
    website = db.Column(db.String(200))
    address = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    transactions = db.relationship('Transaction', backref='location', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    trans_time = db.Column(db.DateTime, default=datetime.now)
    trans_amount = db.Column(db.Float, nullable=False)

def load_users():
    return User.query.all()

def load_locations():
    return Location.query.all()

def load_transactions():
    return Transaction.query.all()

# ----------------------------
# User Registration Endpoint
# ----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        home_address = request.form.get("home_address")
        
        if not username or not password or not home_address:
            flash("Please fill out all fields.")
            return redirect(url_for('register'))
        
        # Geocode the provided home address.
        geocode_result = gmaps.geocode(home_address)
        if not geocode_result:
            flash("Could not find the provided address. Please try a different address.")
            return redirect(url_for('register'))
        
        location = geocode_result[0].get("geometry", {}).get("location", {})
        try:
            latitude = float(location.get("lat"))
            longitude = float(location.get("lng"))
        except (TypeError, ValueError):
            flash("Error processing the provided address.")
            return redirect(url_for('register'))
        
        # Check if the username already exists.
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose a different one.")
            return redirect(url_for('register'))
        
        # Create and store the new user.
        new_user = User(username=username,
                        home_address=home_address,
                        latitude=latitude,
                        longitude=longitude)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for('login'))
    return render_template("register.html", google_maps_api_key=settings.google_maps_api_key)

# ----------------------------
# User Login Endpoint
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.")
            return redirect(url_for('login'))
    return render_template("login.html")

# ----------------------------
# User Logout Endpoint
# ----------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ----------------------------
# Add Transaction Endpoint (Protected)
# ----------------------------
@app.route("/add-transaction", methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == "POST":
        location_id = request.form.get("location_id")
        # The Trasnamount is from 1, 2 or 3 
        # add to the Transaction table with date and time, user id and location id
        user_id = request.form.get("user_id")
        transaction_amount = request.form.get("transaction_amount")
        time_of_transaction = datetime.now()
        
        new_transaction = Transaction(user_id=user_id,
                                        location_id=location_id,
                                        trans_time=time_of_transaction,
                                        trans_amount= transaction_amount)
                                        
        
        
# ----------------------------
# Homepage (Protected)
# ----------------------------
@app.route("/")
@login_required
def index():
    return render_template("index.html",
                           google_maps_api_key=settings.google_maps_api_key,
                           user=current_user)

# ----------------------------
# Helper: Fetch Nearby Businesses
# ----------------------------
def fetch_businesses(lat: float, lng: float, required_count: int):
    all_results = []
    # Define a search radius (2 miles in meters)
    radius = int(5 * 1609.34)
    response = get_nearby_businesses(lat, lng, radius=radius)

    best_radius, counts , n_df= find_radius((lat, lng), response, threshold=17)
    
    print(f"Best radius: {best_radius}")
    print(f"Counts within radius: {counts.sum()}")
    # threshold the response with the best radius
    
    return n_df

    
# ----------------------------
# Endpoint: Paginated Business Listings (Protected)
# ----------------------------
@app.route("/businesses", methods=["POST"])
@login_required
def businesses():
    data = request.get_json()
    user_id = data.get("user_id")
    try:
        page = int(data.get("page", 1))
    except (ValueError, TypeError):
        page = 1

    # Validate that the user_id in the payload matches the logged-in user.
    if not user_id or int(user_id) != current_user.id:
        return jsonify({"error": "Invalid user id"}), 400

    # Retrieve the current user's stored latitude and longitude.
    lat = current_user.latitude
    lng = current_user.longitude

    per_page = 10
    required_count = page * per_page

    # Fetch nearby businesses using the stored coordinates.
    results = fetch_businesses(lat, lng, required_count)
    # print(results)
    total_results = len(results)
    total_pages = (total_results + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    results.to_csv('df.csv')
    
    page_results = results[start:end].to_dict(orient='records')
    print(f'page number: {page}')
    # print(page_results)

    formatted = []
    for business in page_results:
            formatted.append({
                "name": business['name'],
                "address": business['address'],
                "type": business['type'],
                "latitude": business['latitude'],
                "longitude": business['longitude'],
                "distance": business['distance']
            })
        

    return jsonify({
        "businesses": formatted,
        "current_page": page,
        "total_pages": total_pages,
        "total_results": total_results
    })

@app.route("/businesses_table", methods=["GET"])
@login_required
def businesses_table():
    # Retrieve the current user's stored latitude and longitude.
    lat = current_user.latitude
    lng = current_user.longitude
    
    # Set a required count (you can adjust this as needed).
    required_count = 50
    
    # Fetch nearby businesses; note that fetch_businesses returns a DataFrame.
    df = fetch_businesses(lat, lng, required_count)
    df.to_csv('df.csv')
    # Optionally, you can sort or filter the DataFrame here.
    # For example: df = df.sort_values('distance')
    
    # Convert the DataFrame to an HTML table.
    # You can pass CSS classes to style it (here we use Bootstrap classes).
    table_html = df.to_html(classes="table table-striped", index=False)
    
    # Render the table in a template.
    return render_template("businesses_table.html", table_html=table_html)

@app.route("/businesses_all", methods=["POST"])
@login_required
def businesses_all():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id or int(user_id) != current_user.id:
        return jsonify({"error": "Invalid user id"}), 400

    lat = current_user.latitude
    lng = current_user.longitude
    # Set required_count to a high number to get all nearby businesses.
    required_count = 1000  
    # fetch_businesses returns a DataFrame of results.
    results = fetch_businesses(lat, lng, required_count)
    # Format each business as needed.
    formatted = []
    for business in results.to_dict(orient='records'):
        formatted.append({
            "name": business['name'],
            "distance": business['distance'],
            "latitude": business['latitude'],   # for marker placement
            "longitude": business['longitude'],  # for marker placement
            "type": business['type']
        })
    return jsonify({"businesses": formatted})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
