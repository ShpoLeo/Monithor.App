import psycopg2
from psycopg2 import Error
from logger.logs import logger

DB_CONFIG = {
    'dbname': 'storedb',
    'user': 'myuser',
    'password': 'mypassword',
    'host': '127.0.0.1',
    'port': '5432'
} 

def get_db_connection():
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        return None