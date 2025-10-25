# models.py (Corrected Version)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# User model (This model is correct, no changes needed)
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    profile_pic = db.Column(db.String(255), nullable=True)
    preferred_genres = db.Column(db.Text, default="")
    preferred_languages = db.Column(db.Text, default="")
    streaming_platforms = db.Column(db.Text, default="")

    def __repr__(self):
        return f'<User {self.email}>'

# Movie model (This model is mostly correct, review for your needs)
class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(200)) # Increased length for longer titles
    genre = db.Column(db.String(200))
    language = db.Column(db.String(50))
    # CHANGE THIS LINE
    platform = db.Column(db.Text)
    type = db.Column(db.String(50))
    is_trending = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(255))
    release_date = db.Column(db.String(50))
    actors = db.Column(db.Text)
    poster_path = db.Column(db.String(255))
    backdrop_path = db.Column(db.String(255))
    overview = db.Column(db.Text)
    vote_average = db.Column(db.Float)
    vote_count = db.Column(db.Integer)
    trailer_key = db.Column(db.String(100))  
    runtime = db.Column(db.Integer)
    adult = db.Column(db.Boolean, default=False, nullable=False)
    certification = db.Column(db.String(20))          # e.g. "PG-13", "U", "A", "NR"
    certification_country = db.Column(db.String(5))   # e.g. "US", "IN", "GB"
    # NOTE: You have 'vote_average' and 'rating'. Consider if you need both.
    # 'vote_average' from TMDB is usually sufficient.
    rating = db.Column(db.Float) 
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Movie {self.title}>'


# =====================================================================
# === NEW & CORRECTED WATCHLIST MODEL ===
# Replace your old WatchedMovie model with this one.
# =====================================================================
class WatchlistItem(db.Model):
    __tablename__ = 'watchlist_items' # A clearer table name

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # Generic fields to hold info for EITHER a movie or a TV show
    tmdb_id = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(10), nullable=False) # 'movie' or 'tv'
    
    # Store details directly in the table for fast loading
    title = db.Column(db.String(200))
    poster_path = db.Column(db.String(255))
    release_date = db.Column(db.Date, nullable=True)
    vote_average = db.Column(db.Float)
    overview = db.Column(db.Text)
    added_on = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="watchlist_items")

    # Ensure a user can't add the same item twice
    __table_args__ = (db.UniqueConstraint('user_id', 'tmdb_id', 'media_type', name='_user_media_uc'),)

    # The to_dict() method is now correctly inside the class
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'tmdb_id': self.tmdb_id,
            'media_type': self.media_type,
            'title': self.title,
            'name': self.title, # Added for TV show compatibility
            'poster_path': self.poster_path,
            'release_date': self.release_date.strftime('%Y-%m-%d') if self.release_date else None,
            'first_air_date': self.release_date.strftime('%Y-%m-%d') if self.release_date else None, # For TV shows
            'vote_average': self.vote_average,
            'overview': self.overview,
            'added_on': self.added_on.isoformat()
        }
        
    def __repr__(self):
        return f'<WatchlistItem {self.user_id}: {self.media_type} {self.title}>'
# =====================================================================


# Review model (This model is correct, no changes needed)
class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=True)
    tv_id = db.Column(db.Integer, nullable=True) 
    review_text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='user_reviews')