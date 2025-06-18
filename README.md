# Garage Management System

A comprehensive web application for managing garage services, appointments, vehicles, and customers. Built with Flask, MySQL, and modern web technologies.

## Features

- **User Authentication**: Secure login and registration for customers and administrators
- **Vehicle Management**: Add and manage vehicles for service
- **Appointment Scheduling**: Book service appointments with preferred date and time
- **Service Management**: Administrators can add, edit, and remove services
- **Customer Dashboard**: View vehicles, appointments, and available services
- **Admin Dashboard**: Manage services, appointments, vehicles, and customers
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Modern UI**: Clean, minimalist design with smooth animations

## Tech Stack

- **Backend**: Python with Flask framework
- **Database**: MySQL
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Werkzeug security for password hashing
- **Styling**: Custom CSS with responsive design

## Installation

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/garage-management-system.git
   cd garage-management-system
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure the database:
   - Make sure MySQL server is running
   - Copy the example environment file and edit it with your settings:
     ```
     cp env.example .env
     ```
   - Edit the `.env` file with your database credentials and other settings
   - Alternatively, you can set environment variables directly:
     ```
     export MYSQL_PASSWORD=your_password
     export DB_HOST=localhost
     export DB_USER=root
     export DB_NAME=garage_management
     export FLASK_ENV=development  # Options: development, testing, production
     ```
   - If environment variables are not set, you'll be prompted for the password when running the scripts

5. Set up the database:
   - Run the database setup script:
     ```
     python -m database.setup
     ```
   - You can test the database connection with:
     ```
     python -m database.test_connection
     ```

6. Run the application:
   ```
   python app.py
   ```

7. Access the application in your browser:
   ```
   http://localhost:5000
   ```

## Sample User Accounts

### Admin User
- **Email**: admin@garage.com
- **Password**: admin123

### Customer Accounts
- **Email**: john@example.com
- **Password**: password123

- **Email**: sarah@example.com
- **Password**: password123

- **Email**: michael@example.com
- **Password**: password123

- **Email**: emma@example.com
- **Password**: password123

### Staff Account
- **Email**: tech@garage.com
- **Password**: tech123

## Database Configuration

- **Host**: Set via environment variable `DB_HOST` (default: localhost)
- **Username**: Set via environment variable `DB_USER` (default: root)
- **Password**: Set via environment variable `MYSQL_PASSWORD` (default: prompt for password)
- **Database**: Set via environment variable `DB_NAME` (default: garage_management)
- **Environment**: Set via environment variable `FLASK_ENV` (default: development)

## Project Structure

```
garage-management-system/
├── app.py                  # Main application file
├── .env                    # Environment variables (create from env.example)
├── env.example             # Example environment variables
├── database/               # Database scripts
│   ├── __init__.py         # Package initialization
│   ├── config.py           # Configuration settings
│   ├── connection.py       # Database connection module
│   ├── setup.py            # Database setup script
│   └── test_connection.py  # Database connection test script
├── static/                 # Static files
│   ├── css/                # CSS files
│   │   └── style.css       # Main stylesheet
│   ├── js/                 # JavaScript files
│   │   └── main.js         # Main JavaScript file
│   └── images/             # Image files
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── index.html          # Homepage
│   ├── about.html          # About page
│   ├── services.html       # Services page
│   ├── products.html       # Products page
│   ├── contact.html        # Contact page
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── customer_dashboard.html  # Customer dashboard
│   ├── admin_dashboard.html     # Admin dashboard
│   ├── add_vehicle.html         # Add vehicle form
│   ├── schedule_appointment.html # Schedule appointment form
│   └── manage_services.html     # Manage services page
└── requirements.txt        # Python dependencies
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Font Awesome for icons
- Google Fonts for typography
- Unsplash for stock images # GarageManagement
