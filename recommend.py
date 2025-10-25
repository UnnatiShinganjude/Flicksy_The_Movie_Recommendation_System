from difflib import get_close_matches

def get_recommendations(title, cosine_sim, df, indices, top_n=5):
    """
    Finds movies similar to a given title using cosine similarity.
    Returns a tuple of (matched_title, recommendations_list).
    """
    # Get a list of all movie titles from the indices Series
    all_titles = indices.index.tolist()

    # Find the best match for the user's input title
    matches = get_close_matches(title, all_titles, n=1, cutoff=0.6)

    # If no match is found, return an error message and an empty list
    if not matches:
        return "Movie not found in our database.", []

    matched_title = matches[0]
    idx = indices[matched_title]

    # Get similarity scores for the matched movie
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Get the scores of the top_n most similar movies, excluding the movie itself (index 1)
    sim_scores = sim_scores[1:top_n+1]
    movie_indices = [i[0] for i in sim_scores]

    # Return the title that was matched and the list of recommended movie titles
    return matched_title, df['title'].iloc[movie_indices].tolist()