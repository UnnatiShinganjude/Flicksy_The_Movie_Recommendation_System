import os
import requests
import csv

API_KEY = "fec6d2a69059cf2444c7f5d84f38e82d"

BASE_URL = 'https://api.themoviedb.org/3/movie/popular'
GENRE_URL = 'https://api.themoviedb.org/3/genre/movie/list'
TOTAL_PAGES = 10 # Fetches 200 movies (20 per page)

def get_genre_map():
    """Fetches the genre list and returns it as a dictionary for fast lookups."""
    try:
        response = requests.get(GENRE_URL, params={"api_key": API_KEY, "language": "en-US"})
        response.raise_for_status() # Raises an exception for bad status codes (e.g., 401, 404)
        genres_data = response.json()
        # Creates a dictionary for efficient O(1) lookups.
        return {genre['id']: genre['name'] for genre in genres_data['genres']}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching genres: {e}")
        return None

def get_genre_names(genre_ids, genre_map):
    """Translates a list of genre IDs to a comma-separated string of genre names."""
    if not genre_map:
        return ""
    return ", ".join([genre_map.get(gid) for gid in genre_ids if gid in genre_map])

# --- Main script execution ---
print("Fetching movie data from TMDB...")
genre_map = get_genre_map()
movies = []

if genre_map:
    for page in range(1, TOTAL_PAGES + 1):
        print(f"Fetching page {page}/{TOTAL_PAGES}...")
        try:
            response = requests.get(BASE_URL, params={"api_key": API_KEY, "page": page})
            response.raise_for_status() # Adds error handling for each request.
            data = response.json()

            for movie in data.get('results', []):
                movies.append({
                    "id": movie["id"],
                    "title": movie["title"],
                    "overview": movie.get("overview", ""),
                    "genres": get_genre_names(movie.get("genre_ids", []), genre_map),
                    "language": movie.get("original_language", "")
                })
        except requests.exceptions.RequestException as e:
            print(f"Could not fetch page {page}. Error: {e}")

# Save to CSV
if movies:
    with open("movies.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "title", "overview", "genres", "language"])
        writer.writeheader()
        writer.writerows(movies)
    print(f"\nSuccessfully saved {len(movies)} movies to movies.csv")
else:
    print("\nNo movies were fetched. The CSV file was not created.")