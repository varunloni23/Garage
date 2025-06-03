"""
Database package for the Garage Management System.

This package contains modules for database connection, setup, and configuration.
"""

# Import all database functions from the consolidated db module
from .db import get_db_connection, close_connection, execute_query, DatabaseConfig 