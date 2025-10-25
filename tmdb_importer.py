from tmdbv3api import TMDb, Movie as TMDbMovie, TV
from models import db, Movie
from datetime import datetime
import requests
from sqlalchemy.exc import IntegrityError
import time # Import the time module for delays

# --- SETUP ---
tmdb = TMDb()
tmdb.api_key = "YOUR_API_KEY"

tmdb.language = 'en'
tmdb.debug = True

tmdb_movie = TMDbMovie()
tmdb_tv = TV()

# --- CONSTANTS FOR RETRY LOGIC ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# --- FUNCTIONS ---

def fetch_and_store_trending_movies(app):
    """
    Fetches popular movies, gets their details, and stores them in the database.
    Includes retry logic for the main API calls.
    """
    trending = None
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Attempting to fetch popular movies list (Attempt {attempt + 1}/{MAX_RETRIES})...")
            trending = tmdb_movie.popular()
            print("Successfully fetched popular movies list.")
            break # Success, exit the loop
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error fetching popular list: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print("Max retries reached for popular movies list. Aborting.")
                return # Exit the function if we can't get the initial list

    if not trending:
        return

    with app.app_context():
        for m in trending:
            if Movie.query.filter_by(tmdb_id=m.id).first():
                continue

            # Get detailed info with retry logic
            details = None
            for attempt in range(MAX_RETRIES):
                try:
                    details = tmdb_movie.details(m.id)
                    break # Success
                except requests.exceptions.ConnectionError as e:
                    print(f"Connection error fetching details for TMDB ID {m.id}: {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY_SECONDS)
                    else:
                        print(f"Max retries reached for TMDB ID {m.id}. Skipping movie.")
            
            if not details or not getattr(details, 'id', None):
                continue

            # Get trailer and certification (these functions now have their own retry logic)
            trailer_key = get_movie_trailer(details.id)
            certification, cert_country = get_certification(details.id, "US")

            try:
                release_date = datetime.strptime(details.release_date, '%Y-%m-%d') if details.release_date else None
            except (ValueError, TypeError):
                release_date = None

            genres = ", ".join([g['name'] for g in details.genres]) if hasattr(details, 'genres') else ""
            poster_path = f"https://image.tmdb.org/t/p/w500{details.poster_path}" if details.poster_path else None
            backdrop_path = f"https://image.tmdb.org/t/p/w780{details.backdrop_path}" if details.backdrop_path else None

            movie = Movie(
                tmdb_id=details.id,
                title=details.title,
                genre=genres,
                language=details.original_language,
                is_trending=True,
                release_date=release_date,
                link=f"https://www.themoviedb.org/movie/{details.id}",
                poster_path=poster_path,
                backdrop_path=backdrop_path,
                overview=details.overview,
                rating=details.vote_average,
                vote_count=details.vote_count,
                runtime=details.runtime,
                trailer_key=trailer_key,
                certification=certification,
                certification_country=cert_country,
                adult=details.adult
            )
            db.session.add(movie)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("Duplicate found during commit — skipped.")


def get_movie_trailer(movie_id):
    """Fetches the YouTube trailer key for a movie, with retry logic."""
    api_key = tmdb.api_key # Use the globally defined API key
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
    params = {"api_key": api_key, "language": "en-US"}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()

            for video in data.get('results', []):
                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                    return video.get('key')
            return None # Found no trailer, so no need to retry
        except requests.exceptions.ConnectionError as e:
            print(f"Error fetching trailer for movie ID {movie_id} (Attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
        except requests.exceptions.RequestException as e:
            # For other errors like timeouts or bad responses, don't retry
            print(f"A non-connection error occurred fetching trailer for movie ID {movie_id}: {e}")
            break
    
    return None


def get_certification(tmdb_id, region="US"):
    """Fetches the content rating for a movie, with retry logic."""
    api_key = tmdb.api_key
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/release_dates"
    params = {"api_key": api_key}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Search for the target region first
            for entry in data.get("results", []):
                if entry.get("iso_3166_1") == region:
                    for rd in entry.get("release_dates", []):
                        cert = rd.get("certification")
                        if cert and cert.strip():
                            return cert.strip().upper(), region
            
            # If not found, fallback to searching for US certification
            for entry in data.get("results", []):
                if entry.get("iso_3166_1") == "US":
                    for rd in entry.get("release_dates", []):
                        cert = rd.get("certification")
                        if cert and cert.strip():
                            return cert.strip().upper(), "US"
            
            return None, None # Found no certification, no need to retry
        except requests.exceptions.ConnectionError as e:
            print(f"Error fetching certification for movie ID {tmdb_id} (Attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
        except requests.exceptions.RequestException as e:
            print(f"A non-connection error occurred fetching certification for movie ID {tmdb_id}: {e}")
            break
            
    return None, None


# The save_movie function seems to be for a different purpose and doesn't make network calls
# so it doesn't need modification unless it's used elsewhere.
def save_movie(movie_data):
    certification, cert_country = get_certification(movie_data.id, "US")

    movie = Movie(
        tmdb_id=movie_data.id,
        title=getattr(movie_data, "title", None),
        release_date=getattr(movie_data, "release_date", None),
        overview=getattr(movie_data, "overview", None),
        rating=getattr(movie_data, "vote_average", None),
        certification=certification,
        certification_country=cert_country,
        adult=getattr(movie_data, "adult", False)
    )

    db.session.add(movie)

    db.session.commit()
