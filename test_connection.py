
import requests

# IMPORTANT: Replace with your REAL, VALID TMDB API key
API_KEY = "PASTE_YOUR_VALID_TMDB_API_KEY_HERE"
URL = f"https://api.themoviedb.org/3/trending/movie/week?api_key={API_KEY}"

print("--- Running Connection Test ---")
print(f"Attempting to connect to: {URL}")

try:
    # Make the network request with a 10-second timeout
    response = requests.get(URL, timeout=10)

    # Check if the request was successful (e.g., status code 200)
    response.raise_for_status() 

    # If we reach this line, the connection worked!
    print("\n✅ SUCCESS! Connection to TMDB is working correctly from this script.")
    print(f"Status Code: {response.status_code}")

except requests.exceptions.ConnectionError as e:
    # This is the error you have been getting
    print("\n❌ FAILED: A ConnectionError occurred.")
    print("This confirms that something on your computer (like a firewall) is blocking Python's network access.")
    print("This is the same 'ConnectionResetError' issue.")

except requests.exceptions.HTTPError as e:
    # This error means the API key is likely wrong
    print(f"\n❌ FAILED: An HTTPError occurred. Status code: {e.response.status_code}")
    print("This could mean your API key is invalid. Please double-check it on the TMDB website.")

except Exception as e:
    print(f"\n❌ FAILED: An unexpected error occurred: {e}")