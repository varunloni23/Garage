import mysql.connector
from mysql.connector import Error
import os
import getpass
from .config import get_config

def get_db_connection():
    """
    Create and return a connection to the MySQL database.
    
    Returns:
        connection: MySQL connection object if successful, None otherwise
    """
    try:
        # Get configuration
        config = get_config()
        
        # Get database credentials from config
        host = config.DB_HOST
        user = config.DB_USER
        password = config.DB_PASSWORD
        database = config.DB_NAME
        
        # Remove the password prompt and use empty password if not set
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