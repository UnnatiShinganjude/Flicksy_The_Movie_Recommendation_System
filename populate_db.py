# ===================================================================
# ===== THE ULTIMATE populate_db.py SCRIPT ==========================
# ===================================================================

from app import app, db, MovieModel as Movie
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TMDB_API_KEY = "YOUR_API_KEY"
 
GENRE_MAP = {}

# --- Session with retries (no changes) ---
session = requests.Session()
retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# --- Helper functions (no changes) ---
def fetch_genre_map():
    global GENRE_MAP
    if GENRE_MAP: return
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_API_KEY}&language=en-US"
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        genres = response.json().get('genres', [])
        GENRE_MAP = {genre['id']: genre['name'] for genre in genres}
        print("Successfully fetched genre map.")
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch genre map: {e}. Genres will be incorrect.")

def get_certification(tmdb_id, region="US"):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/release_dates?api_key={TMDB_API_KEY}"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for entry in data.get("results", []):
            if entry.get("iso_3166_1") == region:
                for rd in entry.get("release_dates", []):
                    cert = rd.get("certification")
                    if cert and cert.strip(): return cert.strip().upper(), region
        for entry in data.get("results", []):
             for rd in entry.get("release_dates", []):
                cert = rd.get("certification")
                if cert and cert.strip(): return cert.strip().upper(), entry.get("iso_3166_1")
    except requests.exceptions.RequestException: pass
    return None, None

def get_watch_providers(tmdb_id, region="US"):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/watch/providers?api_key={TMDB_API_KEY}"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        providers = data.get("results", {}).get(region, {}).get("flatrate", [])
        if providers:
            provider_names = [p.get("provider_name") for p in providers if p.get("provider_name")]
            return ", ".join(sorted(provider_names))
    except requests.exceptions.RequestException: pass
    return None

# --- Main fetching function (reusable for any query) ---
def fetch_and_save_movies(api_url, description):
    print(f"\nFetching: {description}")
    movies_added_total = 0
    
    for page_num in range(1, 4): # Fetch 3 pages for each combination
        try:
            response = session.get(f"{api_url}&page={page_num}", timeout=15)
            response.raise_for_status()
            movie_list = response.json().get('results', [])
            if not movie_list:
                print(f"  -> No more movies found for this query.")
                break
        except requests.exceptions.RequestException as e:
            print(f"  -> Error fetching page {page_num}: {e}. Stopping.")
            break
        
        movies_added_on_this_page = 0
        for movie_data in movie_list:
            exists = Movie.query.filter_by(tmdb_id=movie_data['id']).first()
            if not exists and movie_data.get('poster_path') and movie_data.get('genre_ids'):
                genre_names = [GENRE_MAP.get(gid) for gid in movie_data['genre_ids'] if GENRE_MAP.get(gid)]
                genre_str = ", ".join(genre_names)
                if not genre_str: continue

                new_movie = Movie(
                    tmdb_id=movie_data['id'],
                    title=movie_data['title'],
                    poster_path=f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}",
                    genre=genre_str,
                    release_date=movie_data.get('release_date', ''),
                    language=movie_data.get('original_language', ''),
                    vote_count=movie_data.get('vote_count', 0),
                    rating=movie_data.get('vote_average', 0.0),
                    overview=movie_data.get('overview', ''),
                    adult=movie_data.get('adult', False),
                    certification=get_certification(movie_data['id'])[0],
                    platform=get_watch_providers(movie_data['id'])
                )
                db.session.add(new_movie)
                movies_added_on_this_page += 1
        
        if movies_added_on_this_page > 0:
            try:
                db.session.commit()
                print(f"  -> Added {movies_added_on_this_page} movies from page {page_num}.")
                movies_added_total += movies_added_on_this_page
            except Exception as e:
                db.session.rollback()
                print(f"  --- DATABASE ERROR: {e} ---")

    if movies_added_total == 0:
        print("  -> No new movies to add for this combination.")


if __name__ == '__main__':
    with app.app_context():
        print("Starting comprehensive database population...")
        fetch_genre_map()
        
        # --- DEFINE THE SCOPE OF YOUR QUIZ ---
        # Match these to the options in your HTML file
        LANGUAGES_TO_FETCH = {'English': 'en', 'Hindi': 'hi', 'Marathi': 'mr', 'Korean': 'ko', 'Tamil': 'ta', 'Telugu': 'te', 'Japanese': 'ja'}
        
        # TMDB Genre IDs
        GENRES_TO_FETCH = {'Action': 28, 'Comedy': 35, 'Drama': 18, 'Horror': 27, 'Romance': 10749}

        # --- SYSTEMATICALLY POPULATE THE DATABASE ---
        for lang_name, lang_code in LANGUAGES_TO_FETCH.items():
            for genre_name, genre_id in GENRES_TO_FETCH.items():
                
                # Construct the specific API URL for this combination
                discover_url = (
                    f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}"
                    f"&with_genres={genre_id}"
                    f"&with_original_language={lang_code}"
                    f"&sort_by=popularity.desc"
                )
                
                description = f"{lang_name} '{genre_name}' movies"
                fetch_and_save_movies(discover_url, description)
            

        print("\nDatabase population script finished!")
