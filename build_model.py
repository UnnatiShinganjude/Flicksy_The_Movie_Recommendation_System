import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

print("Building the content-based model...")

# Load movie data
df = pd.read_csv("movies.csv")

# Handle missing data
df['overview'] = df['overview'].fillna('')
df['genres'] = df['genres'].fillna('')

# Create a "soup" of features for a richer model, weighting genres more heavily.
df['soup'] = df['overview'] + ' ' + (df['genres'].str.replace(',', ' ') * 3)

# TF-IDF Vectorization on the "soup"
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(df['soup'])

# Compute similarity matrix
similarity_matrix = cosine_similarity(tfidf_matrix)

# Create the title-to-index mapping and drop duplicates.
indices = pd.Series(df.index, index=df['title']).drop_duplicates()

# Save the DataFrame, similarity matrix, and indices together in one file.
with open('movie_model.pkl', 'wb') as f:
    pickle.dump((df, similarity_matrix, indices), f)

print("Model built and saved as movie_model.pkl")
