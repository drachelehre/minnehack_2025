from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import settings
import googlemaps, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with a strong secret key.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    # Define a search radius (5 miles in meters)
    radius = int(2 * 1609.34)
    response = gmaps.places_nearby(
        location=(lat, lng),
        radius=radius,
        keyword="business"
    )
    all_results.extend(response.get("results", []))
    
    # Follow next_page_token (if available) until we have enough results.
    while len(all_results) < required_count and "next_page_token" in response:
        next_page_token = response["next_page_token"]
        time.sleep(2)  # Wait for the token to become valid.
        response = gmaps.places_nearby(page_token=next_page_token)
        all_results.extend(response.get("results", []))
    
    return all_results

# ----------------------------
# Endpoint: Paginated Business Listings (Protected)
# ----------------------------
@app.route("/businesses")
@login_required
def businesses():
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid latitude or longitude"}), 400

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    per_page = 10
    required_count = page * per_page
    results = fetch_businesses(lat, lng, required_count)
    total_results = len(results)
    total_pages = (total_results + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    page_results = results[start:end]

    formatted = []
    for business in page_results:
        loc = business.get("geometry", {}).get("location", {})
        formatted.append({
            "name": business.get("name"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng")
        })

    return jsonify({
        "businesses": formatted,
        "current_page": page,
        "total_pages": total_pages,
        "total_results": total_results
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
