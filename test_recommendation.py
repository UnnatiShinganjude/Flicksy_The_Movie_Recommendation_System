import pickle
from recommend import get_recommendations

# Step 1: Load the complete model file
try:
    with open("movie_model.pkl", "rb") as f:
        # Load all three components at once.
        df, similarity_matrix, indices = pickle.load(f)
except FileNotFoundError:
    print("Model file 'movie_model.pkl' not found. Please run build_model.py first.")
    exit()

# Step 2: Get user input
movie_name = input("Enter a movie title to get recommendations: ")

# Step 3: Get recommendations from the refactored function
matched_title, recommended_movies = get_recommendations(movie_name, similarity_matrix, df, indices)

# Step 4: Display the results cleanly
if not recommended_movies:
    print(matched_title) # This will print "Movie not found..." if no matches
else:
    print("-" * 30)
    print(f"Because you watched '{matched_title}', you might like:")
    print("-" * 30)
    for i, movie in enumerate(recommended_movies, 1):
        print(f"{i}. {movie}")
    print("-" * 30)