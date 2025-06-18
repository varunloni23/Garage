# Garage Management System Database Setup

This directory contains the database configuration and setup files for the Garage Management System.

## Using the SQL File on Any Laptop

The `garage_setup.sql` file contains all the necessary SQL commands to set up the complete database structure and sample data. This makes it easy to set up the database on any laptop without needing to run Python code.

### Prerequisites

- MySQL server installed on your laptop
- MySQL client or command-line tool

### Setup Instructions

1. Open a terminal or command prompt
2. Navigate to the directory containing the SQL file
3. Run the SQL file using the MySQL client:

```bash
mysql -u root -p < garage_setup.sql
```

4. When prompted, enter your MySQL root password
5. The script will:
   - Create the `garage_management` database if it doesn't exist
   - Create all necessary tables
   - Insert sample data if the database is empty

### Database Connection in Application

After setting up the database, you'll need to configure your application to connect to it. Create a `.env` file in the project root with the following content:

```
# Database settings
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=garage_management

# Flask settings
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
```

Replace `your_password_here` with your actual MySQL password and `your_secret_key_here` with a secure random string.

## Using the Python Database Module

If you prefer to use the Python database module instead, you can use the following functions:

- `from database import get_db_connection` - Get a database connection
- `from database import execute_query` - Execute SQL queries
- `from database.setup import setup_database` - Set up the complete database

To set up the database using Python:

```python
from database.setup import setup_database
setup_database()
``` 