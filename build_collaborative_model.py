
import pandas as pd
from surprise import Dataset, Reader, SVD
import pickle

print("Building the collaborative filtering model...")

# Load your simulated ratings data (ensure you have created ratings.csv)
try:
    ratings_df = pd.read_csv('ratings.csv')
except FileNotFoundError:
    print("Error: ratings.csv not found. Please create this file with user ratings.")
    exit()

# The Reader class is used to parse the file or dataframe correctly.
# The rating_scale parameter is important for the model to understand the ratings.
reader = Reader(rating_scale=(1, 5))

# The columns must be in the order of: user, item, and rating.
data = Dataset.load_from_df(ratings_df[['user_id', 'movie_id', 'rating']], reader)

# Use the SVD algorithm (a popular matrix factorization method).
algo = SVD()

# Train the algorithm on the entire dataset.
trainset = data.build_full_trainset()
algo.fit(trainset)

# Save the trained model for later use.
with open('collaborative_model.pkl', 'wb') as f:
    pickle.dump(algo, f)

print("Collaborative model built and saved as collaborative_model.pkl")