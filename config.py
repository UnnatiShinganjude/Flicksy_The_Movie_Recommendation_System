# config.py
#DB_USER = 'root'
#DB_PASSWORD = 'Student'  
#DB_HOST = 'localhost'
#DB_NAME = 'movie_recommender'

# config.py
DB_USER = 'root'
DB_PASSWORD = 'Student'  
DB_HOST = '127.0.0.1'  # Use IP instead of 'localhost'
DB_PORT = 3306
DB_NAME = 'movie_recommender'

SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
SQLALCHEMY_TRACK_MODIFICATIONS = False
