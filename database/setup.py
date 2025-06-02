import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os
import getpass
from .config import get_config

def create_database():
    """Create the database if it doesn't exist"""
    config = get_config()
    
    try:
        # Connect to MySQL server without specifying a database
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME}")
            print(f"Database '{config.DB_NAME}' created or already exists.")
            
            cursor.close()
            connection.close()
            
    except Error as e:
        print(f"Error creating database: {e}")

def create_tables():
    """Create all necessary tables for the garage management system"""
    config = get_config()
    
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role ENUM('admin', 'customer') NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create vehicles table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                make VARCHAR(50) NOT NULL,
                model VARCHAR(50) NOT NULL,
                year INT NOT NULL,
                license_plate VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)
            
            # Create services table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create appointments table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                vehicle_id INT NOT NULL,
                service_id INT NOT NULL,
                appointment_date DATETIME NOT NULL,
                notes TEXT,
                status ENUM('pending', 'confirmed', 'completed', 'cancelled') NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
            )
            """)
            
            # Create products table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                stock INT NOT NULL DEFAULT 0,
                image_url VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create invoices table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                appointment_id INT,
                total_amount DECIMAL(10,2) NOT NULL,
                payment_status ENUM('pending', 'paid', 'cancelled') NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
            )
            """)
            
            # Create invoice_items table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_id INT NOT NULL,
                item_type ENUM('service', 'product') NOT NULL,
                item_id INT NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
            """)
            
            print("All tables created successfully.")
            
            cursor.close()
            connection.close()
            
    except Error as e:
        print(f"Error creating tables: {e}")

def insert_sample_data():
    """Insert sample data into the database"""
    config = get_config()
    
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Check if users table is empty
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                # Insert sample users
                admin_password = generate_password_hash('admin123')
                customer_password = generate_password_hash('password123')
                
                cursor.execute("""
                INSERT INTO users (name, email, password, role) VALUES
                ('Admin User', 'admin@garage.com', %s, 'admin'),
                ('John Doe', 'john@example.com', %s, 'customer'),
                ('Jane Smith', 'jane@example.com', %s, 'customer')
                """, (admin_password, customer_password, customer_password))
                
                # Insert sample services
                cursor.execute("""
                INSERT INTO services (name, description, price) VALUES
                ('Oil Change', 'Standard oil change service with filter replacement', 49.99),
                ('Brake Service', 'Inspection and replacement of brake pads if needed', 199.99),
                ('Tire Rotation', 'Rotating tires to ensure even wear', 29.99),
                ('Engine Tune-Up', 'Comprehensive engine tune-up service', 149.99),
                ('Air Conditioning Service', 'AC system check and recharge', 89.99)
                """)
                
                # Insert sample products
                cursor.execute("""
                INSERT INTO products (name, description, price, stock, image_url) VALUES
                ('Motor Oil (5W-30)', 'High-quality synthetic motor oil', 24.99, 50, '/static/img/products/motor-oil.jpg'),
                ('Oil Filter', 'Premium oil filter for most vehicle makes', 9.99, 100, '/static/img/products/oil-filter.jpg'),
                ('Brake Pads', 'Ceramic brake pads for optimal stopping power', 49.99, 30, '/static/img/products/brake-pads.jpg'),
                ('Wiper Blades', 'All-season wiper blades', 19.99, 45, '/static/img/products/wiper-blades.jpg'),
                ('Air Filter', 'Engine air filter for improved performance', 14.99, 60, '/static/img/products/air-filter.jpg')
                """)
                
                # Get user IDs for sample data
                cursor.execute("SELECT id FROM users WHERE email = 'john@example.com'")
                john_id = cursor.fetchone()[0]
                
                # Insert sample vehicles for John
                cursor.execute("""
                INSERT INTO vehicles (user_id, make, model, year, license_plate) VALUES
                (%s, 'Toyota', 'Camry', 2018, 'ABC123'),
                (%s, 'Honda', 'Civic', 2020, 'XYZ789')
                """, (john_id, john_id))
                
                # Get vehicle and service IDs for sample appointments
                cursor.execute("SELECT id FROM vehicles WHERE make = 'Toyota' AND user_id = %s", (john_id,))
                vehicle_id = cursor.fetchone()[0]
                
                cursor.execute("SELECT id FROM services WHERE name = 'Oil Change'")
                service_id = cursor.fetchone()[0]
                
                # Insert sample appointment
                cursor.execute("""
                INSERT INTO appointments (user_id, vehicle_id, service_id, appointment_date, notes, status) VALUES
                (%s, %s, %s, '2023-12-15 10:00:00', 'Please check tire pressure as well', 'confirmed')
                """, (john_id, vehicle_id, service_id))
                
                connection.commit()
                print("Sample data inserted successfully.")
            else:
                print("Database already contains data. Skipping sample data insertion.")
            
            cursor.close()
            connection.close()
            
    except Error as e:
        print(f"Error inserting sample data: {e}")

def setup_database():
    """Set up the complete database"""
    create_database()
    create_tables()
    insert_sample_data()
    print("Database setup completed successfully.")

if __name__ == "__main__":
    setup_database() 