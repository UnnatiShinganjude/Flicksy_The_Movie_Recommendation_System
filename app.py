#app.py
from sqlalchemy import or_, and_, case
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from models import db, User, Movie as MovieModel, Review, WatchlistItem
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from werkzeug.security import generate_password_hash, check_password_hash
from tmdb_importer import fetch_and_store_trending_movies
from tmdbv3api import TMDb, Movie as TMDbMovie
import os,random
import datetime
import requests
from dateutil.relativedelta import relativedelta
import pickle
import pandas as pd
import time
from hybrid_recommend import get_hybrid_recommendations 
import re
from werkzeug.utils import secure_filename

# --- Initial Setup & Configuration ---
try:
    r = requests.get("https://api.themoviedb.org/3/movie/popular?api_key=fec6d2a69059cf2444c7f5d84f38e82d")
    print("TMDB Test Status:", r.status_code)
except Exception as e:
    print("TMDB Test Failed:", e)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_KEY = "fec6d2a69059cf2444c7f5d84f38e82d"
# --- App Configuration ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_super_secret_key_for_dev')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
db.init_app(app)

# --- Load Recommendation Models on Startup ---
# This is done once when the app starts for efficiency.
try:
    print("Loading content-based model (movie_model.pkl)...")
    with open("movie_model.pkl", "rb") as f:
        movies_df, similarity_matrix, indices = pickle.load(f)
    print("Content-based model loaded successfully.")

    print("Loading collaborative filtering model (collaborative_model.pkl)...")
    with open("collaborative_model.pkl", "rb") as f:
        algo = pickle.load(f)
    print("Collaborative filtering model loaded successfully.")

    print("Loading ratings data (ratings.csv)...")
    ratings_df = pd.read_csv('ratings.csv')
    print("Ratings data loaded successfully.")
    MODELS_LOADED = True
except Exception as e:
    print(f"Error loading models: {e}. Recommendation features will be disabled.")
    movies_df, similarity_matrix, indices, algo, ratings_df = [None]*5
    MODELS_LOADED = False

# --- TMDb API and DB Setup ---
tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
movie = TMDbMovie()
# Create tables if they dont exist
with app.app_context():
    db.create_all()

# --- Helper Function for TMDB API Calls ---
# This function reduces a lot of repeated code.


def fetch_from_tmdb(endpoint_path, params={}, max_retries=3):
    """
    Fetches data from a TMDB endpoint with a built-in retry mechanism.
    """
    api_url = f"{TMDB_BASE_URL}/{endpoint_path}"
    default_params = {'api_key': TMDB_API_KEY}
    all_params = {**default_params, **params}

    for attempt in range(max_retries):
        try:
            # Set a timeout to prevent requests from hanging indefinitely
            response = requests.get(api_url, params=all_params, timeout=10)
            
            # This will raise an error for bad status codes like 404 or 401
            response.raise_for_status() 
            
            # If we get here, the request was successful
            return response.json() 

        except (requests.exceptions.RequestException, ConnectionResetError) as e:
            # This block catches network errors and the ConnectionResetError
            print(f"Attempt {attempt + 1} failed for endpoint '{endpoint_path}'. Error: {e}")
            
            if attempt < max_retries - 1:
                # If this wasn't the last attempt, wait before trying again
                time.sleep(2) # Wait 2 seconds
            else:
                # If all attempts fail, print a final error message
                print(f"All {max_retries} attempts failed for endpoint '{endpoint_path}'.")
                return None # Return None to prevent the app from crashing

    return None # Should not be reached, but good practice to have it
# --- Helper Function to Parse Year Ranges ---

def parse_year_range(year_string):
    if not year_string or 'Present' in year_string:
        start_year = re.search(r'(\d{4})', year_string)
        return f"{start_year.group(1)}-01-01", "2099-12-31"
    
    matches = re.findall(r'(\d{4})', year_string)
    if len(matches) == 2:
        return f"{matches[0]}-01-01", f"{matches[1]}-12-31"
    return None, None

# =================================================================
# User Authentication Routes
# =================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    # This route's logic is correct and remains unchanged.
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        if len(password) < 6:
            flash("Password must be at least 6 characters long", "danger")
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash("Email already registered", "danger")
            return redirect(url_for('register'))
           #save new user to database
        new_user = User(full_name=full_name, email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        #Redirect to login page with sucess message
        session['user_id'] = new_user.user_id
        flash("Registration successful! Please complete your profile.", "success")
        return redirect(url_for('setup_profile', user_id=new_user.user_id))
    return render_template("register.html")
# ------------------ User Info ------------------
@app.route('/setup_profile/<int:user_id>', methods=['GET', 'POST'])
def setup_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('register'))
        
    if user.age:
        if 'user_id' in session and session['user_id'] == user_id:
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('login'))

    if request.method == 'POST':
        user.age = request.form.get('age')
        user.mobile = request.form.get('mobile')
        user.preferred_genres = ",".join(request.form.getlist('preferred_genres'))
        user.preferred_languages = ",".join(request.form.getlist('preferred_languages'))
        user.streaming_platforms = ",".join(request.form.getlist('streaming_platforms'))

        # --- START: NEW FILE HANDLING LOGIC ---
        uploaded_file = request.files.get('profile_pic_file')
        avatar_path = request.form.get('profile_pic_path')

        # Priority 1: A new file was uploaded by the user
        if uploaded_file and uploaded_file.filename != '':
            # Secure the filename to prevent security issues
            filename = secure_filename(uploaded_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(save_path)
            # Store the path relative to the static folder so we can load it in templates
            user.profile_pic = os.path.join('uploads', filename).replace("\\", "/")

        # Priority 2: A pre-set avatar was selected (and no new file was uploaded)
        elif avatar_path:
            user.profile_pic = avatar_path
        
            
        db.session.commit()
        flash("Profile created successfully! Please log in to continue.", "success")
        return redirect(url_for('login'))
        
    return render_template('userinfo.html', user=user)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        print("User fetched from DB:", user)
        
        if user:
            print("Entered password:", password)
            print("Stored hash:", user.password_hash)
            print("Password match:", check_password_hash(user.password_hash, password))

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.user_id
            session['user_name'] = user.full_name
            flash("Login successful", "success")
            return render_template('logo.html', redirect_url=url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    # FIX: Also pop user_name for a clean logout
    session.pop('user_name', None)
    flash("You have been logged out", "info")
    return redirect(url_for('login'))


# =================================================================
# Main Application Routes
# =================================================================
# --- Genre Mapping ---
GENRE_MAP = {}
with app.app_context():
    try:
        genre_data = fetch_from_tmdb("genre/movie/list")
        if genre_data and 'genres' in genre_data:
            GENRE_MAP = {genre['id']: genre['name'] for genre in genre_data['genres']}
            print("Successfully fetched and mapped movie genres.")
    except Exception as e:
        print(f"Could not fetch movie genres: {e}")



# --- Language Mapping ---
LANGUAGE_MAP = {}
with app.app_context():
    try:
        language_data = fetch_from_tmdb("configuration/languages")
        if language_data:
            # Create a map of 'english_name': 'iso_639_1'
            LANGUAGE_MAP = {lang['english_name']: lang['iso_639_1'] for lang in language_data}
            print("Successfully fetched and mapped all TMDB languages.")
    except Exception as e:
        print(f"Could not fetch languages: {e}")

# dictionary right below your PLATFORM_PROVIDER_IDS
PLATFORM_COMPANY_IDS = {
    'netflix': 213,   # Netflix Productions
    'prime': 20580,   # Amazon Studios
    'hotstar': 71866  # Hotstar Specials 
}
PLATFORM_PROVIDER_IDS={
    'netflix': 8,
    'prime': 119,
    'hotstar': 122
}

@app.route('/dashboard', defaults={'platform': 'all'})
@app.route('/dashboard/<platform>')
def dashboard(platform):
    # This route was already correct and remains unchanged.
    if 'user_id' not in session:
        flash("Please log in to access the dashboard", "warning")
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    
    
    trending_movies = [] 
    preferred_genre_movies = [] 
    hybrid_recommendations = []
    dynamic_section_movies = [] 
    section_title = "" 
    provider_id = PLATFORM_PROVIDER_IDS.get(platform)

    # 1. Fetch Trending Movies
    if platform == 'all':
        data = fetch_from_tmdb("trending/movie/week", params={"language": "en-US"})
        trending_movies = data.get("results", []) if data else []
    elif provider_id:
        trending_params = {
            'with_watch_providers': provider_id, 'watch_region': 'IN', 'sort_by': 'popularity.desc'
        }
        data = fetch_from_tmdb("discover/movie", params=trending_params)
        trending_movies = data.get("results", []) if data else []

    # 2. Fetch "Upcoming" or "Popular on Platform" Movies
    if platform == 'all':
        section_title = "Upcoming Movies & Series"
        today = datetime.date.today()
        future_date = today + relativedelta(months=+6)
        api_params = {
            'language': 'en-US', 'sort_by': 'primary_release_date.asc',
            'primary_release_date.gte': today.strftime('%Y-%m-%d'),
            'primary_release_date.lte': future_date.strftime('%Y-%m-%d'),
            'with_release_type': '2|3'
        }
        data = fetch_from_tmdb("discover/movie", params=api_params)
        dynamic_section_movies = data.get("results", []) if data else []
    elif provider_id:
        section_title = f"Popular on {platform.title()}"
        api_params = {
            'with_watch_providers': provider_id, 'watch_region': 'IN', 'sort_by': 'popularity.desc'
        }
        data = fetch_from_tmdb("discover/movie", params=api_params)
        dynamic_section_movies = data.get("results", []) if data else []

    for movie in dynamic_section_movies:
        genre_names = [GENRE_MAP.get(gid) for gid in movie.get('genre_ids', []) if GENRE_MAP.get(gid)]
        movie['genres_str'] = ', '.join(genre_names)

    # 3. Fetch "Popular in Your Preferred Genres"
    if user.preferred_genres:
        genre_list = [genre.strip() for genre in user.preferred_genres.split(',')]
        
        match_score = 0
        for g in genre_list:
            match_score += case((MovieModel.genre.ilike(f'%{g}%'), 1), else_=0)
        
        genre_filters = [MovieModel.genre.ilike(f'%{g}%') for g in genre_list]
        
        lang_codes = []
        if user.preferred_languages:
            preferred_langs_list = [lang.strip() for lang in user.preferred_languages.split(',')]
            lang_codes = [LANGUAGE_MAP.get(lang) for lang in preferred_langs_list if LANGUAGE_MAP.get(lang)]

        query = MovieModel.query.filter(or_(*genre_filters))

        if lang_codes:
            query = query.filter(MovieModel.language.in_(lang_codes))

        preferred_genre_movies = query.order_by(
            match_score.desc(),
            MovieModel.vote_count.desc()
        ).limit(8).all()

  


    # 4. Get Hybrid Recommendations
    if MODELS_LOADED:
        try:
            # Get recommendations (title, reasons, and score) from your hybrid function
            recommendations_with_reasons = get_hybrid_recommendations(
                user_id=user.user_id, movies_df=movies_df, ratings_df=ratings_df,
                similarity_matrix=similarity_matrix, indices=indices, algo=algo, n=8
            )

            # Check if we got any recommendations back
            if recommendations_with_reasons:
                # Extract just the titles to query the database
                recommended_titles = [rec['title'] for rec in recommendations_with_reasons]
                
                # Create mappings for reasons AND scores for easy lookup later
                reasons_map = {rec['title']: rec['reasons'] for rec in recommendations_with_reasons}
                scores_map = {rec['title']: rec.get('match_score', 0) for rec in recommendations_with_reasons}

                # Fetch the full movie objects from our database based on the titles
                recommended_movies_from_db = MovieModel.query.filter(MovieModel.title.in_(recommended_titles)).all()

                # Attach both 'reasons' and 'match_score' to each movie object
                for movie in recommended_movies_from_db:
                    movie.reasons = reasons_map.get(movie.title, [])
                    movie.match_score = scores_map.get(movie.title, 0)
                
                # Create a map of title -> movie object to preserve the original sorted order
                title_to_movie_map = {movie.title: movie for movie in recommended_movies_from_db}

                # Build the final list, in the correct order provided by the recommendation function
                hybrid_recommendations = [title_to_movie_map[title] for title in recommended_titles if title in title_to_movie_map]
                
                print(f"Successfully built final list of {len(hybrid_recommendations)} hybrid recommendations.")

        except Exception as e:
            # If anything goes wrong during this process, log the error and continue
            print(f"Error generating hybrid recommendations for user {user.user_id}: {e}")
            # The 'hybrid_recommendations' list will remain empty, so the section won't show

    

    return render_template(
        "dashboard.html", 
        current_user=user, 
        trending=trending_movies,
        preferred_genre_movies=preferred_genre_movies,
        hybrid_recommendations=hybrid_recommendations,
        dynamic_section_movies=dynamic_section_movies,
        section_title=section_title,
        active_platform=platform
    )

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if not user.age:
        flash("Please complete your profile first.", "info")
        return redirect(url_for('setup_profile', user_id=user.user_id))

    # Pass as 'current_user' for template consistency
    return render_template("profile.html", current_user=user)

@app.route('/discover')
def discover():
    # FIX: Fetch user data and pass it to the template.
    user = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
    return render_template('mood_recommendation.html', current_user=user)

@app.route('/watchlist')
def watchlist():
    if 'user_id' not in session:
        flash("Please log in to view your watchlist.", "warning")
        return redirect(url_for('login'))
    # FIX: Fetch user object and pass it to the template as 'current_user'.
    user = db.session.get(User, session['user_id'])
    # You would also fetch actual watchlist items here
    # watchlist_items = WatchlistItem.query.filter_by(user_id=user.user_id).all()
    return render_template('watchlist.html', current_user=user) #, items=watchlist_items)

#------------------------------------------------------

#Search movies
# This now searches movies, TV, and people. 
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    # Using the helper function for consistency
    movies_data = fetch_from_tmdb("search/movie", params={"query": query, "include_adult": False})
    tv_data = fetch_from_tmdb("search/tv", params={"query": query, "include_adult": False})
    people_data = fetch_from_tmdb("search/person", params={"query": query, "include_adult": False})

    return jsonify({
        "movies": movies_data.get("results", []) if movies_data else [],
        "tv_shows": tv_data.get("results", []) if tv_data else [],
        "people": people_data.get("results", []) if people_data else []
    })



import random
from sqlalchemy import or_
from flask import Flask, request, jsonify



@app.route('/mood-recommendations', methods=['POST'])
def mood_recommendations():
    try:
        data = request.get_json()
        print("Finding recommendations for:", data)

        # --- 1. Get User Preferences ---
        mood = data.get('mood', '').strip()
        user_genres = data.get('genres', [])
        year_range = data.get('year', '').strip()
        watching_with = data.get('with_whom', '').strip()
        language = data.get('language', '').strip()
        platform = data.get('platform', '').strip()

        # --- 2. Define Mappings ---
        mood_map = {
            'Happy': ['Comedy', 'Romance', 'Adventure', 'Family', 'Animation', 'Musical'],
            'Normal': ['Action', 'Horror', 'Thriller', 'Fantasy', 'Crime', 'Mystery'],
            'Sad': ['Drama', 'History', 'War', 'Biography', 'Documentary']
        }
        lang_map = {'English': 'en', 'Hindi': 'hi', 'Marathi': 'mr', 'Korean': 'ko', 'Tamil': 'ta', 'Telugu': 'te', 'Japanese': 'ja', 'Other': None}
        ALLOWED_CERTIFICATIONS = {
            "With Family": ["G", "PG", "PG-13", "U", "U/A", "Not Rated", "NR", "12", "U/A 7+", "U/A 13+"],
        }

        # --- 3. Determine Target Genres and Language ---
        # If the user specifically selects genres, we ONLY use those.
        if user_genres:
            target_genres = set(user_genres)
        else:
            # Otherwise, we use the mood as a backup.
            target_genres = set(mood_map.get(mood, []))

        preferred_lang = lang_map.get(language)

        # --- 4. Query and Filter ---
        base_query = MovieModel.query.filter(MovieModel.adult == False)

        if watching_with == "With Family":
            allowed_certs = ALLOWED_CERTIFICATIONS["With Family"]
            family_filter = or_(MovieModel.certification.in_(allowed_certs), MovieModel.certification.is_(None), MovieModel.certification == '')
            base_query = base_query.filter(family_filter)

        if preferred_lang:
            base_query = base_query.filter(MovieModel.language == preferred_lang)
        
        
        if year_range:
            year_filter = None
            if '2020s' in year_range:
                year_filter = MovieModel.release_date >= '2020-01-01'
            elif '2010s' in year_range:
                year_filter = MovieModel.release_date.between('2010-01-01', '2019-12-31')
            elif '2000s' in year_range: # This part was added
                year_filter = MovieModel.release_date.between('2000-01-01', '2009-12-31')
            elif '1990s' in year_range: # This part was added
                year_filter = MovieModel.release_date.between('1990-01-01', '1999-12-31')
            
            if year_filter is not None:
                print(f"Applying year filter for: {year_range}")
                base_query = base_query.filter(year_filter)

        candidate_movies = base_query.limit(1000).all()

        # --- 5. Score and Rank the movies ---
        scored_movies = []
        for movie in candidate_movies:
            movie_genres = set(g.strip() for g in movie.genre.split(',')) if movie.genre else set()
            if movie_genres.intersection(target_genres):
                score = (movie.vote_average or 0) * 5 + min((movie.vote_count or 0) / 100, 30)
                scored_movies.append((movie, score))
        
        scored_movies.sort(key=lambda x: x[1], reverse=True)

        # --- CHANGE 3: Add Variety with a Shuffle ---
        # Get the top 50 best candidates
        top_candidates = [movie for movie, score in scored_movies[:50]]
        # Shuffle that list randomly
        random.shuffle(top_candidates)
        # Pick the first 6 from the shuffled list
        final_results = top_candidates[:6]

        # --- 6. Format and Return the Response ---
        recommended_movies = [{
            'tmdb_id': movie.tmdb_id, 'title': movie.title, 'poster_path': movie.poster_path,
            'vote_average': movie.vote_average, 'release_date': str(movie.release_date)[:4] if movie.release_date else 'N/A'
        } for movie in final_results]
        
        return jsonify(recommended_movies)

    except Exception as e:
        import traceback
        print(f"AN ERROR OCCURRED IN MOOD RECOMMENDATIONS: {e}")
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred"}), 500

#====================================================================
#Person details route


@app.route('/person/<int:person_id>')
def person_details(person_id):
    # 1. Gets the current user (Good practice)
    user = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])

    # 2. Fetches all necessary data from TMDB
    person_data = fetch_from_tmdb(f"person/{person_id}")
    credits_data = fetch_from_tmdb(f"person/{person_id}/combined_credits")
    images_data = fetch_from_tmdb(f"person/{person_id}/images")

    # 3. Handles cases where the person isn't found
    if not person_data:
        flash("Person not found!", "danger")
        return redirect(url_for('dashboard'))

    # 4. Renders the template with the correctly structured data
    return render_template(
        'person_details.html', 
        person=person_data, 
        credits=credits_data,
        person_images=images_data.get('profiles', []) if images_data else [],
        current_user=user 
    )
# ... existing code ...

#watch trailer route
def get_trailer(media_type, media_id):
    """
    Fetches the YouTube trailer key for a given media type (movie or tv) from TMDB.
    Returns the trailer key if found, else None.
    """
    # Validate the media_type to ensure it's either 'movie' or 'tv'
    if media_type not in ['movie', 'tv']:
        return None

    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/videos"
    params = {
        "api_key": TMDB_API_KEY, # Use the global key you defined at the top
        "language": "en-US"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Good practice to check for HTTP errors
        data = response.json()
        for video in data.get("results", []):
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return video.get("key")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching trailer for {media_type} ID {media_id}: {e}")

    return None

# Update this route
@app.route('/trailer/<int:movie_id>')
def show_trailer(movie_id):
    trailer_key = get_trailer('movie', movie_id) # Call the new function
    if trailer_key:
        return render_template('trailer.html', trailer_key=trailer_key)
    else:
        flash("Trailer not found for this movie.", "warning")
        return redirect(url_for('movie_details', movie_id=movie_id)) # Redirect back

# Update this route as well
@app.route('/tv/trailer/<int:tv_id>')
def show_tv_trailer(tv_id):
    trailer_key = get_trailer('tv', tv_id) # Call the new function
    if trailer_key:
        return render_template('trailer.html', trailer_key=trailer_key)
    else:
        flash("Trailer not found for this TV show.", "warning")
        return redirect(url_for('tv_details', tv_id=tv_id)) # Redirect back

# In app.py, add these three new routes

@app.route('/api/movie/<int:movie_id>/cast')
def get_movie_cast(movie_id):
    """API endpoint to get cast for a movie."""
    data = fetch_from_tmdb(f"movie/{movie_id}/credits")
    if data and 'cast' in data:
        return jsonify({'cast': data['cast']}) # Return the cast list under a 'cast' key
    return jsonify({"error": "Cast not found"}), 404

@app.route('/api/movie/<int:movie_id>/platforms')
def get_movie_platforms(movie_id):
    """API endpoint to get watch providers for a movie in India."""
    data = fetch_from_tmdb(f"movie/{movie_id}/watch/providers")
    # The JS expects the 'IN' (India) part of the results
    if data and 'results' in data and 'IN' in data['results']:
        return jsonify(data['results']['IN'])
    return jsonify({"error": "Platform info not found for this region"}), 404

@app.route('/api/movie/<int:movie_id>/reviews')
def get_movie_reviews(movie_id):
    """API endpoint to get reviews for a movie."""
    data = fetch_from_tmdb(f"movie/{movie_id}/reviews")
    if data and 'results' in data:
        return jsonify({'results': data['results']}) # Return reviews under a 'results' key
    return jsonify({"error": "Reviews not found"}), 404





#=====================================================================
#New: watchlist routes
#=====================================================================


@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.get_json()
    media_type = data.get('media_type')
    tmdb_id = data.get('tmdb_id')

    if not media_type or not tmdb_id:
        return jsonify({'error': 'Missing media type or ID'}), 400

    # The initial check is still good practice to prevent unnecessary TMDB lookups
    existing = WatchlistItem.query.filter_by(
        user_id=session['user_id'], 
        tmdb_id=tmdb_id,
        media_type=media_type
    ).first()

    if existing:
        return jsonify({'success': False, 'message': 'Item already in watchlist'}), 200

    # Fetch details from TMDB to store locally
    details = fetch_from_tmdb(f"{media_type}/{tmdb_id}")
    if not details:
        return jsonify({'error': 'Could not find details for this item'}), 404

    # Convert release_date string to a date object
    release_date_str = details.get('release_date') or details.get('first_air_date')
    release_date_obj = None
    if release_date_str:
        try:
            release_date_obj = datetime.datetime.strptime(release_date_str, '%Y-%m-%d').date()
        except ValueError:
            release_date_obj = None

    new_item = WatchlistItem(
        user_id=session['user_id'],
        tmdb_id=tmdb_id,
        media_type=media_type,
        title=details.get('title') or details.get('name'),
        poster_path=details.get('poster_path'),
        release_date=release_date_obj,
        vote_average=details.get('vote_average'),
        overview=details.get('overview')
    )
    db.session.add(new_item)

    try:
        # Try to commit the new item to the database
        db.session.commit()
        return jsonify({'success': True, 'message': 'Added to watchlist'}), 201
    except IntegrityError:
        # If the commit fails due to a duplicate entry (race condition),
        # roll back the session to keep it clean.
        db.session.rollback()
        # Return a success message because the user's goal is met: the item is in the watchlist.
        return jsonify({'success': False, 'message': 'Item already in watchlist'}), 200
  

@app.route('/api/watchlist/remove', methods=['POST'])
def remove_from_watchlist():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.get_json()
    media_type = data.get('media_type')
    tmdb_id = data.get('tmdb_id')

    item_to_remove = WatchlistItem.query.filter_by(  # Changed from WatchedMovie
        user_id=session['user_id'], 
        tmdb_id=tmdb_id,
        media_type=media_type
    ).first()

    if item_to_remove:
        db.session.delete(item_to_remove)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Removed from watchlist'}), 200
    
    return jsonify({'error': 'Item not found in watchlist'}), 404


@app.route('/api/watchlist')
def get_watchlist():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Changed from WatchedMovie
    watchlist_items = WatchlistItem.query.filter_by(user_id=session['user_id']).order_by(WatchlistItem.added_on.desc()).all()
    
    # Convert SQLAlchemy objects to a list of dictionaries
    return jsonify([item.to_dict() for item in watchlist_items])






@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    user = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
    
    movie_data = fetch_from_tmdb(f"movie/{movie_id}")
    if not movie_data:
        flash("Movie not found!", "danger")
        return redirect(url_for('dashboard'))
    
    # --- START OF THE FIX ---

    local_reviews_query = [] # Default to an empty list
    
    # 1. Find the movie in our local database using the TMDB ID from the URL
    movie_in_db = MovieModel.query.filter_by(tmdb_id=movie_id).first()

    # 2. If the movie exists in our database, find all reviews linked to its LOCAL primary key
    if movie_in_db:
        local_reviews_query = Review.query.filter_by(movie_id=movie_in_db.id).order_by(Review.timestamp.desc()).all()
    
    # --- END OF THE FIX ---
    
    local_reviews = []
    for r in local_reviews_query:
        if r.user: 
            local_reviews.append({
                'source': 'Flicksy',
                'author': r.user.full_name,
                'content': r.review_text,
                'rating': r.rating,
                'created_at': r.timestamp.isoformat()
            })

    # The rest of the function remains the same
    api_reviews_data = fetch_from_tmdb(f"movie/{movie_id}/reviews")
    api_reviews = []
    if api_reviews_data and 'results' in api_reviews_data:
        for r in api_reviews_data['results']:
            api_reviews.append({
                'source': 'TMDB',
                'author': r.get('author'),
                'content': r.get('content'),
                'rating': round(r['author_details']['rating'] / 2) if r.get('author_details', {}).get('rating') else None,
                'created_at': r.get('created_at')
            })

    all_reviews = local_reviews + api_reviews
    
    return render_template('movie_details.html', movie=movie_data, reviews=all_reviews, current_user=user)
# In app.py



@app.route('/tv/<int:tv_id>')
def tv_details(tv_id):
    tv_data = fetch_from_tmdb(f"tv/{tv_id}")
    
    if not tv_data:
        flash("TV Show not found!", "danger")
        return redirect(url_for('dashboard'))

    # Fetch user if logged in
    local_reviews_query = Review.query.filter_by(tv_id=tv_id).order_by(Review.timestamp.desc()).all()
    
    local_reviews = []
    for r in local_reviews_query:
        if r.user:
            local_reviews.append({
                'source': 'Flicksy',
                'author': r.user.full_name,
                'content': r.review_text,
                'rating': r.rating,
                'created_at': r.timestamp.isoformat()
            })

    api_reviews_data = fetch_from_tmdb(f"tv/{tv_id}/reviews")
    api_reviews = []
    if api_reviews_data and 'results' in api_reviews_data:
        for r in api_reviews_data['results']:
            api_reviews.append({
                'source': 'TMDB',
                'author': r.get('author'),
                'content': r.get('content'),
                'rating': round(r['author_details']['rating'] / 2) if r.get('author_details', {}).get('rating') else None,
                'created_at': r.get('created_at')
            })

    all_reviews = local_reviews + api_reviews
    
    return render_template('tv_details.html', tv=tv_data, reviews=all_reviews)

# review route for movies
@app.route('/movie/<int:movie_id>/review', methods=['POST'])
def post_movie_review(movie_id):
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to post a review.'}), 401

    user = db.session.get(User, session['user_id'])
    data = request.get_json()
    review_text = data.get('review_text')
    rating = data.get('rating')
    
    if not review_text or not rating:
        return jsonify({'error': 'Review text and a rating are required.'}), 400

    

    # 1. Find the movie in our local database using the TMDB ID.
    #    We assume your Movie model stores the TMDB ID in a column named 'tmdb_id'.
    movie_in_db = MovieModel.query.filter_by(tmdb_id=movie_id).first()

    # 2. If the movie is not in our database, fetch it from TMDB and add it.
    if not movie_in_db:
        print(f"Movie with TMDB ID {movie_id} not in local DB. Fetching and adding.")
        movie_data = fetch_from_tmdb(f"movie/{movie_id}")
        if not movie_data:
            return jsonify({'error': 'Could not find movie details to save.'}), 404
        
        # Create a new Movie object and save it
        new_movie = MovieModel(
            tmdb_id=movie_data['id'],
            title=movie_data['title'],
            overview=movie_data['overview'],
            poster_path=movie_data['poster_path'],
            release_date=datetime.datetime.strptime(movie_data['release_date'], '%Y-%m-%d').date() if movie_data.get('release_date') else None,
            vote_average=movie_data['vote_average'],
            vote_count=movie_data['vote_count'],
            # Add any other fields your MovieModel requires
        )
        db.session.add(new_movie)
        db.session.commit()
        movie_in_db = new_movie # Use the newly created movie object

    # 3. Now check if this user has already reviewed this movie using the local movie's primary key

    existing_review = Review.query.filter_by(user_id=user.user_id, movie_id=movie_in_db.id).first()
    if existing_review:
        return jsonify({'error': 'You have already reviewed this movie.'}), 409

    #Create the review using the local movie's primary key (movie_in_db.id)
    new_review = Review(
        user_id=user.user_id, 
        movie_id=movie_in_db.id, # Use the local DB's primary key
        review_text=review_text, 
        rating=rating
    )
    db.session.add(new_review)
    db.session.commit()

    review_data = {
        'author': user.full_name,
        'content': new_review.review_text,
        'rating': new_review.rating
    }

    return jsonify({
        'message': 'Review submitted successfully!',
        'review': review_data
    }), 201
# review route for tv shoows

@app.route('/tv/<int:tv_id>/review', methods=['POST'])
def post_tv_review(tv_id):
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to post a review.'}), 401

    user = db.session.get(User, session['user_id'])
    data = request.get_json()
    review_text = data.get('review_text') # Match the JS key
    rating = data.get('rating')
    
    if not review_text or not rating:
        return jsonify({'error': 'Review text and a rating are required.'}), 400

    # Check if this user has already reviewed this TV show
    existing_review = Review.query.filter_by(user_id=user.user_id, tv_id=tv_id).first()
    if existing_review:
        return jsonify({'error': 'You have already reviewed this show.'}), 409

    new_review = Review(
        user_id=user.user_id, 
        tv_id=tv_id, 
        review_text=review_text, 
        rating=rating
    )
    db.session.add(new_review)
    db.session.commit()

    # Create a dictionary to send back to the frontend, just like the movie endpoint
    review_data = {
        'author': user.full_name,
        'content': new_review.review_text,
        'rating': new_review.rating
    }

    return jsonify({
        'message': 'Review submitted successfully!',
        'review': review_data
    }), 201

@app.route('/api/tv/<int:tv_id>/cast')
def get_tv_cast(tv_id):
    data = fetch_from_tmdb(f"tv/{tv_id}/credits")
    if data and 'cast' in data:
        return jsonify(data['cast'])
    return jsonify({"error": "Cast not found"}), 404

@app.route('/api/tv/<int:tv_id>/platforms')
def get_tv_platforms(tv_id):
    data = fetch_from_tmdb(f"tv/{tv_id}/watch/providers")
    if data and 'results' in data and 'IN' in data['results']:
        return jsonify(data['results']['IN'])
    return jsonify({"error": "Platform info not found"}), 404










# =================================================================
# Helper for Static Pages
# =================================================================
def render_static_page(template_name):
    """Helper function to avoid repeating code for static pages."""
    user = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
    return render_template(template_name, current_user=user)

@app.route('/contact-us')
def contact():
   
    return render_static_page('contact.html')

@app.route('/faq')
def faq():

    return render_static_page('faq2.html')

@app.route('/privacy-policy')
def privacypolicy():
    
    return render_static_page('privacypolicy.html')

@app.route('/terms')
def terms():
    
    return render_static_page('terms.html')


# =================================================================
# Main Execution Block
# =================================================================
if __name__ == '__main__':
    # --- Configuration should be done BEFORE running the app ---
    UPLOAD_FOLDER = 'static/uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    # -----------------------------------------------------------

    with app.app_context():
        db.create_all()
        # fetch_and_store_trending_movies(app)
    
    # Run the app AFTER all setup is complete
    app.run(debug=False, host="0.0.0.0", port=5501)