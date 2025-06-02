#!/usr/bin/env python3
from database.setup import setup_database

if __name__ == "__main__":
    print("Initializing Garage Management System database...")
    setup_database()
    print("Database initialization complete!") 