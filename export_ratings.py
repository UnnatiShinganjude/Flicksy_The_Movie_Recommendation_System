
import pandas as pd
from app import app, db  
from models import Review, Movie 

def export_ratings_to_csv():
    """
    Queries the database for all user reviews and exports them to a ratings.csv file.
    It also ensures that the movie_id in the ratings maps to the tmdb_id required
    by the recommendation models.
    """
    with app.app_context():
        print("Connecting to the database and fetching reviews...")
        
        # Query the reviews table to get user_id, movie_id (from our db), and rating
        # We join with the Movie table to get the tmdb_id
        reviews_query = db.session.query(
            Review.user_id, 
            Movie.tmdb_id, 
            Review.rating
        ).join(Movie, Review.movie_id == Movie.id).filter(Review.rating.isnot(None)).all()

        if not reviews_query:
            print("No reviews with ratings found in the database. Cannot create ratings.csv.")
            return

        # Create a DataFrame with the correct column names for the model
        # The model expects 'movie_id' to be the TMDB ID.
        ratings_df = pd.DataFrame(reviews_query, columns=['user_id', 'movie_id', 'rating'])
        
        # Save the DataFrame to a CSV file, which will be used by the collaborative model
        ratings_df.to_csv('ratings.csv', index=False)
        
        print(f"Successfully exported {len(ratings_df)} ratings to ratings.csv")

if __name__ == '__main__':
    export_ratings_to_csv()
