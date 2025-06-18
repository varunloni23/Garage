-- Garage Management System Database Setup
-- This SQL file can be used to set up the complete database structure on any laptop
-- Run with: mysql -u root -p < garage_setup.sql

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS garage_management;

-- Use the database
USE garage_management;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'customer') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    license_plate VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create services table
CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create appointments table
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
);

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    appointment_id INT,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_status ENUM('pending', 'paid', 'cancelled') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
);

-- Create cart_items table
CREATE TABLE IF NOT EXISTS cart_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_product (user_id, product_id)
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method ENUM('cash_on_delivery', 'upi', 'credit_card', 'debit_card') NOT NULL,
    payment_status ENUM('pending', 'paid', 'failed', 'refunded') NOT NULL DEFAULT 'pending',
    delivery_address TEXT NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    order_status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') NOT NULL DEFAULT 'pending',
    upi_transaction_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price_per_unit DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Create invoice_items table
CREATE TABLE IF NOT EXISTS invoice_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    item_type ENUM('service', 'product') NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- Insert sample data (only if tables are empty)

-- Check if users table is empty
SET @user_count = (SELECT COUNT(*) FROM users);

-- Only insert sample data if no users exist
DELIMITER //
CREATE PROCEDURE insert_sample_data()
BEGIN
    IF @user_count = 0 THEN
        -- Insert sample admin user (password: admin123)
        -- Note: In a real application, you should use proper password hashing
        -- This is just a placeholder password hash for demo purposes
        INSERT INTO users (name, email, password, role) VALUES
        ('Admin User', 'admin@garage.com', '$2b$12$tG5XjlFXfGYQkdK8Hl.W9.CRRIEbKuGYxFXQXTcIGkH1G6sr1.3YG', 'admin'),
        ('John Doe', 'john@example.com', '$2b$12$1FYiGNO6EOOO2RGDZpfSVOY2.GRJcbvgQaJJIiB0kQJS.XlFcQKlS', 'customer'),
        ('Jane Smith', 'jane@example.com', '$2b$12$1FYiGNO6EOOO2RGDZpfSVOY2.GRJcbvgQaJJIiB0kQJS.XlFcQKlS', 'customer');
        
        -- Insert sample services
        INSERT INTO services (name, description, price) VALUES
        ('Oil Change', 'Standard oil change service with filter replacement', 49.99),
        ('Brake Service', 'Inspection and replacement of brake pads if needed', 199.99),
        ('Tire Rotation', 'Rotating tires to ensure even wear', 29.99),
        ('Engine Tune-Up', 'Comprehensive engine tune-up service', 149.99),
        ('Air Conditioning Service', 'AC system check and recharge', 89.99);
        
        -- Insert sample products
        INSERT INTO products (name, description, price, stock, image_url) VALUES
        ('Motor Oil (5W-30)', 'High-quality synthetic motor oil', 24.99, 50, '/static/img/products/motor-oil.jpg'),
        ('Oil Filter', 'Premium oil filter for most vehicle makes', 9.99, 100, '/static/img/products/oil-filter.jpg'),
        ('Brake Pads', 'Ceramic brake pads for optimal stopping power', 49.99, 30, '/static/img/products/brake-pads.jpg'),
        ('Wiper Blades', 'All-season wiper blades', 19.99, 45, '/static/img/products/wiper-blades.jpg'),
        ('Air Filter', 'Engine air filter for improved performance', 14.99, 60, '/static/img/products/air-filter.jpg');
        
        -- Get user ID for John
        SET @john_id = (SELECT id FROM users WHERE email = 'john@example.com');
        
        -- Insert sample vehicles for John
        INSERT INTO vehicles (user_id, make, model, year, license_plate) VALUES
        (@john_id, 'Toyota', 'Camry', 2018, 'ABC123'),
        (@john_id, 'Honda', 'Civic', 2020, 'XYZ789');
        
        -- Get vehicle and service IDs for sample appointments
        SET @vehicle_id = (SELECT id FROM vehicles WHERE make = 'Toyota' AND user_id = @john_id);
        SET @service_id = (SELECT id FROM services WHERE name = 'Oil Change');
        
        -- Insert sample appointment
        INSERT INTO appointments (user_id, vehicle_id, service_id, appointment_date, notes, status) VALUES
        (@john_id, @vehicle_id, @service_id, '2023-12-15 10:00:00', 'Please check tire pressure as well', 'confirmed');
    END IF;
END //
DELIMITER ;

-- Call the procedure to insert sample data
CALL insert_sample_data();

-- Clean up
DROP PROCEDURE IF EXISTS insert_sample_data;

-- Confirm completion
SELECT 'Garage Management Database Setup Complete' AS Message; 