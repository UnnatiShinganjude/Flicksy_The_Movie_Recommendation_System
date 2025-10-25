import pandas as pd
from recommend import get_recommendations

def get_hybrid_recommendations(user_id, movies_df, ratings_df, similarity_matrix, indices, algo, n=10):
    """
    Generates hybrid recommendations with specific reasons for each movie.
    """
    print(f"Generating hybrid recommendations for User ID: {user_id}")
    
    # NEW: The recommendations dictionary will now store scores and a set of reasons
    recommendations = {}

    # --- 1. Collaborative Filtering Recommendations ---
    all_movie_ids = movies_df['id'].unique()
    watched_movie_ids = ratings_df[ratings_df['user_id'] == user_id]['movie_id'].unique()
    unwatched_movie_ids = [mid for mid in all_movie_ids if mid not in watched_movie_ids]

    collaborative_preds = [algo.predict(user_id, movie_id) for movie_id in unwatched_movie_ids]
    collaborative_preds.sort(key=lambda x: x.est, reverse=True)

    for pred in collaborative_preds[:n]:
        movie_title = movies_df.loc[movies_df['id'] == pred.iid, 'title'].iloc[0]
        # Initialize the movie in our dictionary
        if movie_title not in recommendations:
            recommendations[movie_title] = {'score': 0, 'reasons': set()}
        # Add the score and the reason
        recommendations[movie_title]['score'] += pred.est
        recommendations[movie_title]['reasons'].add("Highly rated by users like you")

    # --- 2. Content-Based Recommendations ---
    try:
        user_ratings = ratings_df[ratings_df['user_id'] == user_id]
        if not user_ratings.empty:
            top_movie_id = user_ratings.sort_values(by='rating', ascending=False).iloc[0]['movie_id']
            top_movie_title = movies_df.loc[movies_df['id'] == top_movie_id, 'title'].iloc[0]
            
            print(f"Seed movie for content-based part: {top_movie_title}")
            _, content_recs = get_recommendations(top_movie_title, similarity_matrix, movies_df, indices, top_n=n)

            for i, title in enumerate(content_recs):
                # Initialize the movie if it's not already there
                if title not in recommendations:
                    recommendations[title] = {'score': 0, 'reasons': set()}
                # Add a content-based score and the specific reason
                recommendations[title]['score'] += 4.0 - (i * 0.1)
                recommendations[title]['reasons'].add(f"Because you liked '{top_movie_title}'")

    except (IndexError, KeyError) as e:
        print(f"Could not generate content-based part for User {user_id}. Reason: {e}")

    # --- 3. Combine and Rank ---
    # Sort recommendations by the combined score
    sorted_recommendations = sorted(recommendations.items(), key=lambda item: item[1]['score'], reverse=True)

    # NEW: Return a list of dictionaries, each containing the title and the list of reasons
    import pandas as pd
from recommend import get_recommendations

def get_hybrid_recommendations(user_id, movies_df, ratings_df, similarity_matrix, indices, algo, n=10):
    """
    Generates hybrid recommendations with specific reasons for each movie.
    """
    print(f"Generating hybrid recommendations for User ID: {user_id}")
    
    # NEW: The recommendations dictionary will now store scores and a set of reasons
    recommendations = {}

    # --- 1. Collaborative Filtering Recommendations ---
    all_movie_ids = movies_df['id'].unique()
    watched_movie_ids = ratings_df[ratings_df['user_id'] == user_id]['movie_id'].unique()
    unwatched_movie_ids = [mid for mid in all_movie_ids if mid not in watched_movie_ids]

    collaborative_preds = [algo.predict(user_id, movie_id) for movie_id in unwatched_movie_ids]
    collaborative_preds.sort(key=lambda x: x.est, reverse=True)

    for pred in collaborative_preds[:n]:
        movie_title = movies_df.loc[movies_df['id'] == pred.iid, 'title'].iloc[0]
        # Initialize the movie in our dictionary
        if movie_title not in recommendations:
            recommendations[movie_title] = {'score': 0, 'reasons': set()}
        # Add the score and the reason
        recommendations[movie_title]['score'] += pred.est
        recommendations[movie_title]['reasons'].add("Highly rated by users like you")

    # --- 2. Content-Based Recommendations ---
    try:
        user_ratings = ratings_df[ratings_df['user_id'] == user_id]
        if not user_ratings.empty:
            top_movie_id = user_ratings.sort_values(by='rating', ascending=False).iloc[0]['movie_id']
            top_movie_title = movies_df.loc[movies_df['id'] == top_movie_id, 'title'].iloc[0]
            
            print(f"Seed movie for content-based part: {top_movie_title}")
            _, content_recs = get_recommendations(top_movie_title, similarity_matrix, movies_df, indices, top_n=n)

            for i, title in enumerate(content_recs):
                # Initialize the movie if it's not already there
                if title not in recommendations:
                    recommendations[title] = {'score': 0, 'reasons': set()}
                # Add a content-based score and the specific reason
                recommendations[title]['score'] += 4.0 - (i * 0.1)
                recommendations[title]['reasons'].add(f"Because you liked '{top_movie_title}'")

    except (IndexError, KeyError) as e:
        print(f"Could not generate content-based part for User {user_id}. Reason: {e}")

    # --- 3. Combine and Rank ---
    # Sort recommendations by the combined score
    sorted_recommendations = sorted(recommendations.items(), key=lambda item: item[1]['score'], reverse=True)

    # NEW: Return a list of dictionaries, including a calculated match_score
    final_recs = []
    for title, data in sorted_recommendations[:n]:
        # Convert the raw score into a percentage.
        # We cap it at 100%. You can adjust the divisor (e.g., 5.0) if your scores are higher.
        match_percentage = min((data['score'] / 5.0) * 100, 100)
        
        final_recs.append({
            'title': title,
            'reasons': list(data['reasons']),
            'match_score': match_percentage  # Add the new key here
        })
        
    return final_recs