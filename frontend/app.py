from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from config import settings
import googlemaps, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from utils.fetch_data import get_nearby_businesses
from utils.radius_calc import find_radius
import random
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with a strong secret key.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
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
    __tablename__ = "user"
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
        total_rewards = sum([(transaction.trans_amount +3*max(0,transaction.trans_left_a_review) )for transaction in transactions])
        self.cummulative_reward = total_rewards
    @property
    def total_stars(self):
        """
        Compute total stars from all transactions.
        Conditions for a transaction to award stars:
          - Star 1: if trans_amount is not 0 or -1.
          - Star 2: if trans_visited_here is True.
          - Star 3: if trans_left_a_review is not -1 or 0.
        """
        transactions = Transaction.query.filter_by(user_id=self.id).all()
        stars = 0
        for t in transactions:
            star1 = 1 if t.trans_amount not in [0, -1] else 0
            star2 = 1 if t.trans_visited_here else 0
            star3 = 1 if t.trans_left_a_review not in [-1, 0] else 0
            stars += (star1 + star2 + star3)
        return stars
        

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Location(db.Model):
    __tablename__ = "location"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    business_type = db.Column(db.String(100))
    website = db.Column(db.String(200))
    address = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    transactions = db.relationship('Transaction', backref='location', lazy=True)

class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    trans_time = db.Column(db.DateTime, default=datetime.utcnow)
    trans_amount = db.Column(db.Float, nullable=False) # -1 = did not buy anything 
    trans_visited_here = db.Column(db.Boolean, nullable=False) # 1 or 0 for if they visited here
    trans_left_a_review = db.Column(db.Integer, nullable=False) # -1 = did not leave a review


def load_users():
    return User.query.all()

def load_locations():
    return Location.query.all()

def load_transactions():
    return Transaction.query.all()

# ----------------------------
# User Registration Endpoint
# ----------------------------
BRAND_CAPTCHAS = [
    {"name": "google", "image": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg"},
    {"name": "amazon", "image": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"},
    {"name": "meta", "image": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Meta_Platforms_Inc._logo.svg"}
]

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        # Check captcha response.
        captcha_response = request.form.get("captcha_response", "").strip().lower()
        if captcha_response != "solved":
            flash("Captcha not resolved. Please solve the captcha correctly.")
            return redirect(url_for('register'))
        
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
        
        # Automatically log the new user in.
        login_user(new_user)
        flash("Registration successful. You are now logged in.")
        return redirect(url_for('index'))
    
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
        # Get the form values.
        location = Location.query.filter_by(name=request.form.get("businessName")).first()
        location_id = location.id if location else None
        user_id = request.form.get("user_id")
        
        # Check if the "visited" checkbox is checked.
        visited_value = request.form.get("visited")
        if visited_value == "on":
            trans_visited_here = True
            # For a pure visit (without purchase), set trans_amount to 0 so it won't count as a purchase.
            trans_amount = 0  
        else:
            trans_visited_here = False
            trans_amount = -1

        # Get the review rating. If no review is selected, default to -1.
        review_rating = request.form.get("review_rating")
        if review_rating and review_rating.strip() != "":
            trans_left_a_review = int(review_rating)
        else:
            trans_left_a_review = -1

        # Process the photo upload (not stored in our Transaction model in this example).
        photo = request.files.get("photo")
        # Use the current time for the transaction.
        time_of_transaction = datetime.now()

        # Create the new Transaction object.
        new_transaction = Transaction(
            user_id=user_id,
            location_id=location_id,
            trans_time=time_of_transaction,
            trans_amount=trans_amount,
            trans_visited_here=trans_visited_here,
            trans_left_a_review=trans_left_a_review
        )

        # Add the transaction to the session.
        db.session.add(new_transaction)
        
        # Update the user’s cumulative reward.
        user = User.query.get(user_id)
        user.calculate_rewards()
        
        # Commit the changes.
        db.session.commit()
        
        flash("Transaction submitted successfully!")
        return redirect(url_for('index'))
    
    # For GET, redirect to the index (since the modal form is on index.html)
    return redirect(url_for('index'))


                                        

 
        
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

    per_page = 5
    required_count = page * per_page

    # Fetch nearby businesses using the stored coordinates.
    results = fetch_businesses(lat, lng, required_count)
    total_results = len(results)
    total_pages = (total_results + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    # (Optional) save dataframe for debugging
    results.to_csv('df.csv')
    
    page_results = results[start:end].to_dict(orient='records')
    print(f'page number: {page}')

    formatted = []
    for business in page_results:
        # Default stars is 0/3 if no transaction is found.
        stars = 0
        # Try to find a Location record matching this business name.
        location = Location.query.filter_by(name=business['name']).first()
        if location:
            # print(f'++++++++++++++++++{current_user.id}+++++++++++++++++++')
            transactions = Transaction.query.filter_by(user_id=current_user.id,
                                                       location_id=location.id).all()
            
            if transactions:
                # Condition 1: at least one transaction with a valid trans_amount.
                star1 = 1 if any(t.trans_amount not in [0, -1] for t in transactions) else 0
                # Condition 2: at least one transaction where the user visited.
                star2 = 1 if any(t.trans_visited_here for t in transactions) else 0
                # Condition 3: at least one transaction with a valid review.
                star3 = 1 if any(t.trans_left_a_review not in [-1, 0] for t in transactions) else 0
                stars = star1 + star2 + star3

        # Otherwise, stars remains 0.
        
        formatted.append({
            "name": business['name'],
            "address": business['address'],
            "type": business['type'],
            "latitude": business['latitude'],
            "longitude": business['longitude'],
            "distance": business['distance'],
            "stars": f"{stars}/3"  # add the stars field
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

    # Get the user's latitude and longitude.
    lat = current_user.latitude
    lng = current_user.longitude

    # Set required_count to a high number to get all nearby businesses.
    required_count = 1000  
    # fetch_businesses returns a DataFrame of results.
    results = fetch_businesses(lat, lng, required_count)

    formatted = []
    for business in results.to_dict(orient='records'):
        # Default star rating is 0.
        stars = 0

        # Try to find a matching Location record using the business name.
        location = Location.query.filter_by(name=business['name']).first()

        # If the location is not in the database, create and upload it.
        if not location:
            location = Location(
                name=business['name'],
                address=business.get('address', ''),
                business_type=business.get('type', ''),
                latitude=business.get('latitude'),
                longitude=business.get('longitude')
            )
            db.session.add(location)
            db.session.commit()  # Commit so that location gets an ID.

        # Now, query for any transactions by the current user at this location.
        transactions = Transaction.query.filter_by(user_id=current_user.id,
                                                   location_id=location.id).all()
        if transactions:
            # Condition 1: At least one transaction with trans_amount not in [0, -1].
            star1 = 1 if any(t.trans_amount not in [0, -1] for t in transactions) else 0
            # Condition 2: At least one transaction where trans_visited_here is True.
            star2 = 1 if any(t.trans_visited_here for t in transactions) else 0
            # Condition 3: At least one transaction with trans_left_a_review not in [-1, 0].
            star3 = 1 if any(t.trans_left_a_review not in [-1, 0] for t in transactions) else 0
            stars = star1 + star2 + star3

        # Build the star string using Unicode characters:
        filled_star = "★"  # U+2605
        empty_star = "☆"   # U+2606
        star_string = filled_star * stars + empty_star * (3 - stars)

        formatted.append({
            "name": business['name'],
            "distance": business['distance'],
            "latitude": business['latitude'],
            "longitude": business['longitude'],
            "type": business['type'],
            "stars": star_string
        })
        
    return jsonify({"businesses": formatted})

@app.route("/rewards")
@login_required
def rewards():
    # Example reward items with image URLs.
    reward_items = [
        {
            "name": "Free Coffee",
            "cost": 10,
            "description": "Redeem 10 stars for a free coffee.",
            "image_url": "data:image/png;base64,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"
        },
        {
            "name": "Gift Card",
            "cost": 25,
            "description": "Redeem 25 stars for a $5 gift card.",
            "image_url": "data:image/png;base64,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"
        },
        {
            "name": "Movie Ticket",
            "cost": 50,
            "description": "Redeem 50 stars for a free movie ticket.",
            "image_url": "data:image/png;base64,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"
        },
        {
            "name": "Lunch Special",
            "cost": 75,
            "description": "Redeem 75 stars for a discounted lunch.",
            "image_url": "https://i.etsystatic.com/22005614/r/il/988f22/4566007434/il_570xN.4566007434_psbb.jpg"
        },
        {
            "name": "Exclusive T-Shirt",
            "cost": 100,
            "description": "Redeem 100 stars for an exclusive T-Shirt.",
            "image_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMwAAADACAMAAAB/Pny7AAAAaVBMVEUAAAD////R0dGjo6P4+Pj19fV1dXXr6+vw8PBpaWn7+/t6enp+fn5wcHBkZGRcXFyEhIQWFhaKiori4uJVVVXBwcG0tLSpqak+Pj41NTXHx8cODg4uLi5GRkaTk5MlJSVNTU0cHBybm5tVHoq7AAAE9ElEQVR4nO3d2ZaiMBAG4CCrNAoKuLbr+z/kgC0iUFmKQUg89V/OORPyTUiCkGSY9UVhU1dgyBBG1/TBuLPN1t7ajWw3M6dfDR6lNcsqS3N7FNUDs4l2DMhpnfe4vpUnJ6i0XbTBl4XGuN4vdPEy+zX68k7ELe3XQzc1FuPGvIuXmWMvLywtxt5qSIzYwhiybSJxaVgNDiOzsBuq3+QrSXEx7k5DYXyZpei4PqI4cCBpahDF4TD+XHpxxrJAubhMobg5RoPApAuFizO2TBWLWyoVt1AsDodJPaWLF21zCOWlhQeVdinjqWuUMb6qpZhvbOn10/teuThP+U5Txfhq99gz861wUA22Kr3vlYVqN1TEuGo3+Cu3xZb77+nbiyOutKXifKOGwVpKTpYcgFnCPSSZbHYBNGrzjRKmh6XM7yk+528NlObn+MR9FhNrlNpGBdPT8sjqdtlfs+s1O+0vN3yT1BqVtlHABP9hGS5LhVFAjsGNY5/LQj5CSzGI+eXDkc83Moz/M7Whzo9MI8HoZJFrxJhAk/5SxROPAkKMg3rqGCNz4QgtwrjaWYoxTaQRYHS0iDV8jKNZf6ki0HAxgZbtUmbBfU7jYfSZK7vhjmkcjC95ozVtIs58A2P0tjCWwBoQo7ulaBvwToMwrsb9pcoPNAoAGBMsxSgAjNBdjGOEBdR0MK6mc2U3XU0bY0q7lOloWhgz+kuV9ijQxARa/RaTpzVCNzB+MnXtsEkCHsY8S0vzhgkMtBQaF8K4hvWXKpHTxTjaP4/xUmsqjGNou5R5aZj5llrDDL/H/hKFNcY13FK1DTN2TG7mMd8UmGA9dU2GyDooMeF56noMk3NYYPKpazFUcos56qsLNM/OYYep6zBcZsz4UbnOmn3NXcYYuHKVokX6Lf/QMnv2BY8yVZLvGprDy9R1GCr7kFmbqSsxVIrHGcv5kl6zdh4/Ab5CkwTPH2df8EgTBdXP5sCo1+VQ/j5AP19oaPvRXy3PJTXVezOjNdW2ndcbTYM1ry1I9btmYzX1dqoaExqqmYcAxrBPgFXeF9K8f2wy7SNgmcayzeZnQOM0zSWozQ+0Oi/MgtJa6tz6dK7vkjko89ZyoPaiBunmRY3S2cbZXTujxTYGlcSdqgOrmgxpm64FXG9mhAawgBjHgDsN3BwELmvUbQtAN/AGQc6CU+58M+pExK8FYsEpX2PPPlVxKLM7/Oe8bUHcRdrgnXYPx8XAnyi5W5y4y+d9YBQ4O9a4GMsFPh7zt9LxNza4nZ3U6+KXw8gY4K1e1mNjQ5GW5nGkxNgYy2ppMkGFhTub3mfP29/xGONjrORtJ/QRmivVMNb6+izoFj+PgZkAY9nVbujj9SysrmQ3YHr3llk8j+zqAXUKjOXbXpxlS+8uOWdAuuk0TNP0bSicBFPWYpam0gMgsIfoTIRRC2EIQxjCEIYwhCEMYQhDGMIQhjCEIQxhCEMYwhCGMIQhDGEIQxjCEIYwhCEMYQhDGMIQhjCEIQxhCEMYwhCGMIQhDGEIQxjCEIYwhCEMYQhDGMIQhjCEIYxWmHRMjOTIjP/GWGNi0HXD/oXdeJbrxzEjHomefxxjrcayXNBVw2PSo7weQ2SF7f59MNZmlP+x4hd9k/XChHnnsLDhk/Ww9MGUJzgtP9pzVkvZqUwDYgpOvrU/lm3ei9Ibo2cIo2u+CvMPvl9XeiHR1sUAAAAASUVORK5CYII="
        }
    ]
    return render_template("rewards.html", reward_items=reward_items)



if __name__ == '__main__':
    with app.app_context():
        print('-------------------')
        migrate = Migrate(app, db)
        print(db.create_all())

    app.run(debug=True)
