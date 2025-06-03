import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class DatabaseConfig:
    """Database configuration class."""
    # Database settings
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_USER = os.environ.get('DB_USER') or 'root'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or ''
    DB_NAME = os.environ.get('DB_NAME') or 'garage_management'

    @classmethod
    def get_config(cls, env=None):
        """
        Get database configuration based on environment.
        
        Args:
            env (str): Environment name (development, testing, production)
            
        Returns:
            DatabaseConfig: Configuration instance
        """
        if env == 'testing':
            # Override database name for testing
            cls.DB_NAME = 'garage_management_test'
        elif env == 'production':
            # Ensure password is set in production
            if not cls.DB_PASSWORD:
                print("Warning: No DB_PASSWORD set for Production environment")
        
        return cls

def get_db_connection():
    """
    Create and return a connection to the MySQL database.
    
    Returns:
        connection: MySQL connection object if successful, None otherwise
    """
    try:
        # Get configuration
        env = os.environ.get('FLASK_ENV') or 'development'
        config = DatabaseConfig.get_config(env)
        
        # Get database credentials from config
        host = config.DB_HOST
        user = config.DB_USER
        password = config.DB_PASSWORD
        database = config.DB_NAME
        
        # Use empty password if not set
        if not password:
            password = ''
            print("Warning: Using empty MySQL password. Set DB_PASSWORD environment variable if needed.")
        
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        
        if connection.is_connected():
            return connection
        
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def close_connection(connection, cursor=None):
    """
    Close the database connection and cursor.
    
    Args:
        connection: MySQL connection object
        cursor: MySQL cursor object (optional)
    """
    if cursor:
        cursor.close()
    
    if connection and connection.is_connected():
        connection.close()

def execute_query(query, params=None, fetch=False, commit=False, return_last_id=False):
    """
    Execute a SQL query and optionally fetch results or commit changes.
    
    Args:
        query (str): SQL query to execute
        params (tuple): Parameters for the query (optional)
        fetch (bool): Whether to fetch and return results
        commit (bool): Whether to commit changes to the database
        return_last_id (bool): Whether to return the last inserted ID
        
    Returns:
        list: Query results if fetch=True
        int: Last inserted ID if return_last_id=True
        None: Otherwise
    """
    connection = get_db_connection()
    cursor = None
    result = None
    last_id = None
    
    try:
        if connection:
            cursor = connection.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if fetch:
                result = cursor.fetchall()
            
            if return_last_id:
                last_id = cursor.lastrowid
                
            if commit:
                connection.commit()
                
    except Error as e:
        print(f"Error executing query: {e}")
        
    finally:
        close_connection(connection, cursor)
        
    if return_last_id:
        return last_id
    else:
        return result 