import os
import pyrebase
import math
import pandas as pd
from flask import Flask, jsonify, render_template, request, redirect, flash, session
from datetime import datetime

gen_key = os.urandom(24)  # Generates a 24-byte random key

app = Flask(__name__)
app.secret_key = gen_key # Required for flash messages

firebase_config = {
  "apiKey": os.environ.get('API_KEY'),
  "authDomain": os.environ.get('AUTH_DOMAIN'),
  "databaseURL": os.environ.get('DATABASE_URL'),
  "projectId": os.environ.get('PROJECT_ID'),
  "storageBucket": os.environ.get('STORAGE_BUCKET'),
  "messagingSenderId": os.environ.get('MESSAGING_SENDER_ID'),
  "appId": os.environ.get('APP_ID'),
  "measurementId": os.environ.get('MEASUREMENT_ID')
    }


# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)

storage = firebase.storage()
auth = firebase.auth()
db = firebase.database()

# Replace 'file.csv' with your file path
places = pd.read_csv('places.csv')

def choose(df):
    if len(session['chosen_ids']) == len(df):
        return None
    row = df.sample(n=1)
    chosen_id = int(row.loc[row.index[0], 'id'])
    while chosen_id in session['chosen_ids']:
        row = df.sample(n=1)
        chosen_id = int(row.loc[row.index[0], 'id'])
    session['chosen_ids'].append(chosen_id)
    return row

def calculate_distance(lat1, lon1, lat2, lon2):
    # Calculate the distance between two points on the Earth using the Haversine formula
    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers (mean radius)
    r = 6371
    return c * r

# Function to get users with average scores
def get_sorted_users():
    users = db.child("users").get()  # Adjust path if necessary

    # Create a list of tuples (username, average_score)
    user_scores = []
    
    for user in users.each():
        username = user.val().get('username')  # Assuming you have a field 'username'
        average_score = user.val().get('average_score')  # Assuming field is 'average_score'
        
        # Ensure both fields exist
        if username and average_score is not None:
            user_scores.append((username, average_score))

    # Sort the list by average_score in decreasing order
    sorted_user_scores = sorted(user_scores, key=lambda x: x[1], reverse=True)
    
    return sorted_user_scores

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get the form data
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')
        username = request.form.get('username')
        fullname = request.form.get('fullname')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect('/signup')

        try:
            # Create a new user with Firebase Authentication
            user = auth.create_user_with_email_and_password(email, password)
            flash('Signup successful! You can now log in.', 'success')
            print(user)
             # Add user data to Realtime Database
            user_data = {
                "username": username,
                "email": email,
                "createdAt": str(datetime.now()),
                "fullname": fullname
            }
            
            # Store data under '/users/{user["localId"]}'
            db.child(f'users/{user["localId"]}').set(user_data)
            return redirect('/signup')
        except Exception as e:
            # Handle exceptions (e.g., email already in use, weak password)
            flash(f'Email already registered', 'danger')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Verify user's email and password via Firebase Authentication
            user = auth.sign_in_with_email_and_password(email, password)

            # Check if user exists in Firebase
            if user:
                # Store user info in the session
                session['localId'] = user["localId"]

                # Fetch user details from the Realtime Database
                user_data = db.child(f'users/{user["localId"]}').get().val() 
                
                # Store user's data in the session for use in the landing page
                session['username'] = user_data.get('username')
                
                flash('Login successful!', 'success')
                return redirect('/landing')  # Redirect to landing page after login
        except Exception as e:
            flash(f'Invalid Email or Password', 'danger')
    return render_template('login.html')

@app.route('/landing')
def landing():
    # Check if user is logged in by verifying session
    session['chosen_ids'] = []
    sorted_users = get_sorted_users()
    leaderboard = [(index + 1, username, score) for index, (username, score) in enumerate(sorted_users)]
    print(leaderboard)
    if 'localId' in session:
        user_data = db.child("users").child(session['localId']).get().val()

        if 'highscore' in user_data:
            highscore = user_data.get('highscore')
        else:
            highscore = "none"
        session['highscore'] = highscore

        if 'average_score' in user_data:
            average_score = user_data.get('average_score')
            number_of_games = user_data.get('number_of_games')
        else:
            average_score = "none"
            number_of_games = 0
        session['average_score'] = average_score
        session['number_of_games'] = number_of_games

        # Determine the user's rank
        user_rank = None
        for index, (username, score) in enumerate(sorted_users):
            if username == session['username']:
                user_rank = index + 1  # Rank is index + 1 (1-based)
                break

        # Debugging output
        print(f"User Rank: {user_rank} for username: {session['username']}")
        # Display the logged-in user's information from the session
        return render_template('landing.html', 
                               username=session['username'],
                               highscore=highscore,
                               average_score=average_score,
                               leaderboard=leaderboard,
                               user_rank=user_rank)
    else:
        # If no user is logged in, redirect to login page
        flash('Please log in first.', 'warning')
        return redirect('/login')

@app.route('/game')
def game():
    return render_template('game.html', username=session['username'], highscore=session['highscore'], average_score=session['average_score'])

@app.route('/get_place', methods=['GET'])
def get_place():
    # Get the place ID from the URL query parameter
    place = choose(places)
    
    if place is None:
        return jsonify({'message': 'No more places to show!'})
    else:
        # Assuming 'Image Base64' contains the Base64 encoded image
        image_base64 = str(place.loc[place.index[0], 'Compressed Image Base64'])
        session['latitude'] = place.loc[place.index[0], 'Latitude']
        session['longitude'] = place.loc[place.index[0], 'Longitude']
        session['place-name'] = place.loc[place.index[0], 'Name']
        session['place-location'] = place.loc[place.index[0], 'Location']
        print(type(image_base64))
        print(session['chosen_ids'])
        # Send the Base64 string directly to the frontend
        return jsonify({'place': image_base64})

@app.route('/get_score', methods=['GET', 'POST'])
def get_score():
    if request.method == 'POST':
        data = request.get_json()

        # Extract latitude and longitude
        lat = data.get('lat')
        lon = data.get('lon')

        # Calculate the distance between the actual location and the user's guess
        distance = calculate_distance(session['latitude'], session['longitude'], float(lat), float(lon))
        distance = round(distance, 2)
        print(distance)

        # Calculate the score based on the distance
        score = math.exp((20075 - distance) / 4358.9)
        score = round(score, 2)
        print(score)

        if score > 100:
            score = 100
        if score < 0:
            score = 0

        # Check if the user has a highscore
        if session['highscore'] != "none":
            if score > session['highscore']:
                # Update the highscore in the Realtime Database
                db.child("users").child(session['localId']).update({"highscore": score})
                session['highscore'] = score
        else:
            # Add the highscore to the Realtime Database
            db.child("users").child(session['localId']).update({"highscore": score})
            session['highscore'] = score

        # Calculate the average score
        if session['average_score'] != "none":
            number_of_games = session['number_of_games']
            average_score = session['average_score']
            new_average_score = (average_score * number_of_games + score) / (number_of_games + 1)
            new_average_score = round(new_average_score, 2)
            session['average_score'] = new_average_score
            session['number_of_games'] = number_of_games+1
            # Update the average score in the Realtime Database
            db.child("users").child(session['localId']).update({"average_score": new_average_score})
            db.child("users").child(session['localId']).update({"number_of_games": number_of_games + 1})
        else:
            # Add the average score to the Realtime Database
            db.child("users").child(session['localId']).update({"average_score": score})
            db.child("users").child(session['localId']).update({"number_of_games": 1})
            session['average_score'] = score
            session['number_of_games'] = 1

        return jsonify({'score': score, 'distance': distance, 'average_score': session['average_score'], 
        'highscore': session['highscore'], 'lat': session['latitude'], 'lon': session['longitude'], 'place_name': session['place-name'], 'place_location': session['place-location']})

@app.route('/logout')
def logout():
    # Clear session data to log out the user
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
