from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database.connection import get_db_connection, close_connection, execute_query
from database.config import get_config
from werkzeug.utils import secure_filename

# Create Flask app
app = Flask(__name__)

# Load configuration
config = get_config()
app.secret_key = config.SECRET_KEY
app.debug = config.DEBUG

# Define allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check if a filename has an allowed extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Context processor to add current date and time to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Context processor to add cart count to all templates
@app.context_processor
def inject_cart_count():
    cart_count = 0
    if 'user_id' in session:
        user_id = session['user_id']
        result = execute_query(
            'SELECT COUNT(*) as count FROM cart_items WHERE user_id = %s',
            (user_id,),
            fetch=True
        )
        if result and result[0]['count']:
            cart_count = result[0]['count']
    return {'cart_count': cart_count}

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/products')
def products():
    products_data = execute_query('SELECT * FROM products', fetch=True)
    
    # Check if products_data is None (database query failed)
    if products_data is None:
        flash('Unable to retrieve products. Please try again later.', 'danger')
        products_data = []  # Initialize as empty list to avoid TypeError
    
    # Process image URLs for products
    for product in products_data:
        if product['image_url']:
            product['image_url'] = url_for('static', filename=product['image_url'])
        else:
            # Default image if none is set
            product['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    return render_template('products.html', products=products_data)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        
        # Here you would typically save the contact form data to the database
        # or send an email to the administrator
        
        flash('Your message has been sent! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = execute_query('SELECT * FROM users WHERE email = %s', (email,), fetch=True)
        
        if user is None:
            flash('Database connection error. Please try again later.', 'danger')
            return render_template('login.html')
        
        if not user:
            flash('No user found with this email address', 'danger')
            return render_template('login.html')
            
        user = user[0]  # Get the first (and only) user
        
        # Debug information
        if app.debug:
            print(f"Login attempt for: {email}")
            print(f"Password hash in DB: {user['password'][:20]}...")
            print(f"Hash method used: {user['password'].split('$')[0]}")
        
        if check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = 'customer'  # Default role
        
        # Validate password
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Check password length and complexity
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return render_template('register.html')
        
        # Use scrypt method to match existing user password hashing
        hashed_password = generate_password_hash(password, method='scrypt')
        
        try:
            result = execute_query(
                'INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)',
                (name, email, hashed_password, role),
                commit=True
            )
            
            if result is None:
                flash('Database connection error. Please try again later.', 'danger')
                return render_template('register.html')
                
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Registration failed: {err}', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# Dashboard routes
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    if session['user_role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('customer_dashboard'))

@app.route('/dashboard/admin')
def admin_dashboard():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get services
    services = execute_query('SELECT * FROM services', fetch=True)
    if services is None:
        services = []
        flash('Unable to retrieve services data. Database connection error.', 'danger')
    
    # Get appointments
    appointments = execute_query('''
        SELECT a.*, u.name as customer_name, s.name as service_name, v.make, v.model 
        FROM appointments a 
        JOIN users u ON a.user_id = u.id 
        JOIN services s ON a.service_id = s.id
        JOIN vehicles v ON a.vehicle_id = v.id
        ORDER BY a.appointment_date DESC
    ''', fetch=True)
    if appointments is None:
        appointments = []
        flash('Unable to retrieve appointments data. Database connection error.', 'danger')
    
    # Get vehicles
    vehicles = execute_query('''
        SELECT v.*, u.name as owner_name 
        FROM vehicles v 
        JOIN users u ON v.user_id = u.id
    ''', fetch=True)
    if vehicles is None:
        vehicles = []
        flash('Unable to retrieve vehicles data. Database connection error.', 'danger')
    
    # Get customers
    customers = execute_query('''
        SELECT u.*, 
            (SELECT COUNT(*) FROM vehicles WHERE user_id = u.id) as vehicle_count,
            (SELECT COUNT(*) FROM appointments WHERE user_id = u.id) as appointment_count
        FROM users u
        WHERE u.role = 'customer'
        ORDER BY u.name
    ''', fetch=True)
    if customers is None:
        customers = []
        flash('Unable to retrieve customers data. Database connection error.', 'danger')
    
    # Get products
    products = execute_query('SELECT * FROM products ORDER BY name', fetch=True)
    if products is None:
        products = []
        flash('Unable to retrieve products data. Database connection error.', 'danger')
    
    # Process image URLs for products
    for product in products:
        if product['image_url']:
            product['image_url'] = url_for('static', filename=product['image_url'])
        else:
            # Default image if none is set
            product['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    return render_template('admin_dashboard.html', 
                          services=services, 
                          appointments=appointments, 
                          vehicles=vehicles,
                          customers=customers,
                          products=products)

@app.route('/dashboard/customer')
def customer_dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get user's vehicles
    vehicles = execute_query('SELECT * FROM vehicles WHERE user_id = %s', (user_id,), fetch=True)
    if vehicles is None:
        vehicles = []
        flash('Unable to retrieve vehicles data. Database connection error.', 'danger')
    
    # Get user's appointments
    appointments = execute_query('''
        SELECT a.*, s.name as service_name, v.make, v.model 
        FROM appointments a 
        JOIN services s ON a.service_id = s.id 
        JOIN vehicles v ON a.vehicle_id = v.id 
        WHERE a.user_id = %s
        ORDER BY a.appointment_date DESC
    ''', (user_id,), fetch=True)
    if appointments is None:
        appointments = []
        flash('Unable to retrieve appointments data. Database connection error.', 'danger')
    
    # Get available services
    services = execute_query('SELECT * FROM services', fetch=True)
    if services is None:
        services = []
        flash('Unable to retrieve services data. Database connection error.', 'danger')
    
    return render_template('customer_dashboard.html', 
                          vehicles=vehicles, 
                          appointments=appointments, 
                          services=services)

# Vehicle management
@app.route('/vehicles/add', methods=['GET', 'POST'])
def add_vehicle():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        license_plate = request.form['license_plate']
        user_id = session['user_id']
        
        try:
            execute_query(
                'INSERT INTO vehicles (make, model, year, license_plate, user_id) VALUES (%s, %s, %s, %s, %s)',
                (make, model, year, license_plate, user_id),
                commit=True
            )
            flash('Vehicle added successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to add vehicle: {err}', 'danger')
    
    return render_template('add_vehicle.html')

@app.route('/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
def edit_vehicle(vehicle_id):
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get the vehicle and verify ownership
    vehicle = execute_query(
        'SELECT * FROM vehicles WHERE id = %s AND user_id = %s', 
        (vehicle_id, user_id), 
        fetch=True
    )
    
    if not vehicle:
        flash('Vehicle not found or you do not have permission to edit it', 'danger')
        return redirect(url_for('customer_dashboard'))
    
    vehicle = vehicle[0]  # Get the first (and only) vehicle
    
    if request.method == 'POST':
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        license_plate = request.form['license_plate']
        
        try:
            execute_query(
                'UPDATE vehicles SET make = %s, model = %s, year = %s, license_plate = %s WHERE id = %s AND user_id = %s',
                (make, model, year, license_plate, vehicle_id, user_id),
                commit=True
            )
            flash('Vehicle updated successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to update vehicle: {err}', 'danger')
    
    return render_template('edit_vehicle.html', vehicle=vehicle)

# Appointment management
@app.route('/appointments/schedule', methods=['GET', 'POST'])
def schedule_appointment():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get user's vehicles
    vehicles = execute_query('SELECT * FROM vehicles WHERE user_id = %s', (user_id,), fetch=True)
    
    # Get available services
    services = execute_query('SELECT * FROM services', fetch=True)
    
    # Check if vehicle_id or service_id was passed in the URL
    vehicle_id = request.args.get('vehicle_id')
    service_id = request.args.get('service_id')
    
    if request.method == 'POST':
        vehicle_id = request.form['vehicle_id']
        service_id = request.form['service_id']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        notes = request.form['notes']
        
        # Combine date and time
        appointment_datetime = f"{appointment_date} {appointment_time}"
        
        try:
            execute_query(
                '''INSERT INTO appointments 
                (user_id, vehicle_id, service_id, appointment_date, notes, status) 
                VALUES (%s, %s, %s, %s, %s, %s)''',
                (user_id, vehicle_id, service_id, appointment_datetime, notes, 'pending'),
                commit=True
            )
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to schedule appointment: {err}', 'danger')
    
    return render_template('schedule_appointment.html', vehicles=vehicles, services=services, 
                          selected_vehicle_id=vehicle_id, selected_service_id=service_id)

@app.route('/appointments/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
def reschedule_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get the appointment and verify ownership
    appointment = execute_query(
        '''SELECT a.*, s.name as service_name, v.make, v.model 
           FROM appointments a 
           JOIN services s ON a.service_id = s.id 
           JOIN vehicles v ON a.vehicle_id = v.id 
           WHERE a.id = %s AND a.user_id = %s AND a.status IN ('pending', 'confirmed')''',
        (appointment_id, user_id),
        fetch=True
    )
    
    if not appointment:
        flash('Appointment not found, already completed, or you do not have permission to reschedule it', 'danger')
        return redirect(url_for('customer_dashboard'))
    
    appointment = appointment[0]  # Get the first (and only) appointment
    
    if request.method == 'POST':
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        notes = request.form['notes']
        
        # Combine date and time
        appointment_datetime = f"{appointment_date} {appointment_time}"
        
        try:
            execute_query(
                'UPDATE appointments SET appointment_date = %s, notes = %s WHERE id = %s AND user_id = %s',
                (appointment_datetime, notes, appointment_id, user_id),
                commit=True
            )
            flash('Appointment rescheduled successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to reschedule appointment: {err}', 'danger')
    
    # Format the date and time for the form
    appointment_date = appointment['appointment_date'].strftime('%Y-%m-%d')
    appointment_time = appointment['appointment_date'].strftime('%H:%M')
    
    return render_template('reschedule_appointment.html', 
                          appointment=appointment,
                          appointment_date=appointment_date,
                          appointment_time=appointment_time)

@app.route('/appointments/cancel/<int:appointment_id>', methods=['GET', 'POST'])
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get the appointment and verify ownership
    appointment = execute_query(
        '''SELECT a.*, s.name as service_name, v.make, v.model 
           FROM appointments a 
           JOIN services s ON a.service_id = s.id 
           JOIN vehicles v ON a.vehicle_id = v.id 
           WHERE a.id = %s AND a.user_id = %s AND a.status IN ('pending', 'confirmed')''',
        (appointment_id, user_id),
        fetch=True
    )
    
    if not appointment:
        flash('Appointment not found, already completed/cancelled, or you do not have permission to cancel it', 'danger')
        return redirect(url_for('customer_dashboard'))
    
    appointment = appointment[0]  # Get the first (and only) appointment
    
    if request.method == 'POST':
        try:
            execute_query(
                'UPDATE appointments SET status = %s WHERE id = %s AND user_id = %s',
                ('cancelled', appointment_id, user_id),
                commit=True
            )
            flash('Appointment cancelled successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to cancel appointment: {err}', 'danger')
    
    return render_template('cancel_appointment.html', appointment=appointment)

@app.route('/appointments/details/<int:appointment_id>')
def appointment_details(appointment_id):
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get the appointment and verify ownership
    appointment = execute_query(
        '''SELECT a.*, s.name as service_name, s.description as service_description, s.price as service_price,
           v.make, v.model, v.year, v.license_plate
           FROM appointments a 
           JOIN services s ON a.service_id = s.id 
           JOIN vehicles v ON a.vehicle_id = v.id 
           WHERE a.id = %s AND (a.user_id = %s OR %s = (SELECT id FROM users WHERE role = 'admin' AND id = %s))''',
        (appointment_id, user_id, user_id, user_id),
        fetch=True
    )
    
    if not appointment:
        flash('Appointment not found or you do not have permission to view it', 'danger')
        return redirect(url_for('customer_dashboard'))
    
    appointment = appointment[0]  # Get the first (and only) appointment
    
    return render_template('appointment_details.html', appointment=appointment)

# Service management (admin only)
@app.route('/services/manage', methods=['GET', 'POST'])
def manage_services():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        # Check if it's an edit request
        if 'edit_id' in request.form:
            service_id = request.form['edit_id']
            name = request.form['edit_name']
            description = request.form['edit_description']
            price = request.form['edit_price']
            
            try:
                execute_query(
                    'UPDATE services SET name = %s, description = %s, price = %s WHERE id = %s',
                    (name, description, price, service_id),
                    commit=True
                )
                flash('Service updated successfully!', 'success')
            except mysql.connector.Error as err:
                flash(f'Failed to update service: {err}', 'danger')
        
        # Check if it's a delete request
        elif 'delete_id' in request.form:
            service_id = request.form['delete_id']
            
            try:
                execute_query('DELETE FROM services WHERE id = %s', (service_id,), commit=True)
                flash('Service deleted successfully!', 'success')
            except mysql.connector.Error as err:
                flash(f'Failed to delete service: {err}', 'danger')
        
        # Otherwise, it's an add request
        else:
            name = request.form['name']
            description = request.form['description']
            price = request.form['price']
            
            try:
                execute_query(
                    'INSERT INTO services (name, description, price) VALUES (%s, %s, %s)',
                    (name, description, price),
                    commit=True
                )
                flash('Service added successfully!', 'success')
            except mysql.connector.Error as err:
                flash(f'Failed to add service: {err}', 'danger')
    
    # Get all services
    services = execute_query('SELECT * FROM services', fetch=True)
    
    return render_template('manage_services.html', services=services)

# Admin appointment management
@app.route('/admin/appointments/view/<int:appointment_id>')
def admin_view_appointment(appointment_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get detailed appointment information
    appointment = execute_query(
        '''SELECT a.*, u.name as customer_name, u.email as customer_email, 
           s.name as service_name, s.description as service_description, s.price as service_price,
           v.make, v.model, v.year, v.license_plate
           FROM appointments a 
           JOIN users u ON a.user_id = u.id 
           JOIN services s ON a.service_id = s.id 
           JOIN vehicles v ON a.vehicle_id = v.id 
           WHERE a.id = %s''',
        (appointment_id,),
        fetch=True
    )
    
    if not appointment:
        flash('Appointment not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    appointment = appointment[0]  # Get the first (and only) appointment
    
    return render_template('admin_appointment_details.html', appointment=appointment)

@app.route('/admin/appointments/schedule', methods=['GET', 'POST'])
def admin_schedule_appointment():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get all customers
    customers = execute_query('SELECT * FROM users WHERE role = %s ORDER BY name', ('customer',), fetch=True)
    
    # Get available services
    services = execute_query('SELECT * FROM services', fetch=True)
    
    # Check if customer_id was passed in the URL
    customer_id = request.args.get('customer_id')
    service_id = request.args.get('service_id')
    
    # If customer_id is provided, get their vehicles
    vehicles = []
    if customer_id:
        vehicles = execute_query('SELECT * FROM vehicles WHERE user_id = %s', (customer_id,), fetch=True)
    
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        vehicle_id = request.form['vehicle_id']
        service_id = request.form['service_id']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        notes = request.form['notes']
        
        # Combine date and time
        appointment_datetime = f"{appointment_date} {appointment_time}"
        
        try:
            execute_query(
                '''INSERT INTO appointments 
                (user_id, vehicle_id, service_id, appointment_date, notes, status) 
                VALUES (%s, %s, %s, %s, %s, %s)''',
                (customer_id, vehicle_id, service_id, appointment_datetime, notes, 'confirmed'),
                commit=True
            )
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to schedule appointment: {err}', 'danger')
    
    return render_template('admin_schedule_appointment.html', 
                          customers=customers,
                          vehicles=vehicles,
                          services=services, 
                          selected_customer_id=customer_id,
                          selected_service_id=service_id)

@app.route('/admin/appointments/edit/<int:appointment_id>', methods=['GET', 'POST'])
def admin_edit_appointment(appointment_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get appointment information
    appointment = execute_query(
        '''SELECT a.*, u.name as customer_name, u.id as customer_id, 
           s.name as service_name, s.id as service_id,
           v.make, v.model, v.id as vehicle_id
           FROM appointments a 
           JOIN users u ON a.user_id = u.id 
           JOIN services s ON a.service_id = s.id 
           JOIN vehicles v ON a.vehicle_id = v.id 
           WHERE a.id = %s''',
        (appointment_id,),
        fetch=True
    )
    
    if not appointment:
        flash('Appointment not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    appointment = appointment[0]  # Get the first (and only) appointment
    
    # Get all services for the dropdown
    services = execute_query('SELECT * FROM services', fetch=True)
    
    # Get customer's vehicles for the dropdown
    vehicles = execute_query(
        'SELECT * FROM vehicles WHERE user_id = %s',
        (appointment['customer_id'],),
        fetch=True
    )
    
    if request.method == 'POST':
        vehicle_id = request.form['vehicle_id']
        service_id = request.form['service_id']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        status = request.form['status']
        notes = request.form['notes']
        
        # Combine date and time
        appointment_datetime = f"{appointment_date} {appointment_time}"
        
        try:
            execute_query(
                '''UPDATE appointments 
                   SET vehicle_id = %s, service_id = %s, appointment_date = %s, 
                       status = %s, notes = %s 
                   WHERE id = %s''',
                (vehicle_id, service_id, appointment_datetime, status, notes, appointment_id),
                commit=True
            )
            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('admin_view_appointment', appointment_id=appointment_id))
        except mysql.connector.Error as err:
            flash(f'Failed to update appointment: {err}', 'danger')
    
    # Format the date and time for the form
    appointment_date = appointment['appointment_date'].strftime('%Y-%m-%d')
    appointment_time = appointment['appointment_date'].strftime('%H:%M')
    
    return render_template('admin_edit_appointment.html', 
                          appointment=appointment,
                          services=services,
                          vehicles=vehicles,
                          appointment_date=appointment_date,
                          appointment_time=appointment_time)

@app.route('/admin/appointments/update-status/<int:appointment_id>', methods=['POST'])
def admin_update_appointment_status(appointment_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    status = request.form.get('status')
    if status not in ['pending', 'confirmed', 'completed', 'cancelled']:
        flash('Invalid status', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        execute_query(
            'UPDATE appointments SET status = %s WHERE id = %s',
            (status, appointment_id),
            commit=True
        )
        flash('Appointment status updated successfully!', 'success')
    except mysql.connector.Error as err:
        flash(f'Failed to update appointment status: {err}', 'danger')
    
    return redirect(url_for('admin_dashboard'))

# Admin Service Management
@app.route('/admin/services/view/<int:service_id>')
def admin_view_service(service_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get service details
    service = execute_query('SELECT * FROM services WHERE id = %s', (service_id,), fetch=True)
    
    if not service:
        flash('Service not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    service = service[0]  # Get the first (and only) service
    
    # Get count of appointments using this service
    appointment_count = execute_query(
        'SELECT COUNT(*) as count FROM appointments WHERE service_id = %s',
        (service_id,),
        fetch=True
    )[0]['count']
    
    return render_template('admin_service_details.html', service=service, appointment_count=appointment_count)

@app.route('/admin/services/edit/<int:service_id>', methods=['GET', 'POST'])
def admin_edit_service(service_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get service details
    service = execute_query('SELECT * FROM services WHERE id = %s', (service_id,), fetch=True)
    
    if not service:
        flash('Service not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    service = service[0]  # Get the first (and only) service
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        
        try:
            execute_query(
                'UPDATE services SET name = %s, description = %s, price = %s WHERE id = %s',
                (name, description, price, service_id),
                commit=True
            )
            flash('Service updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to update service: {err}', 'danger')
    
    return render_template('admin_edit_service.html', service=service)

@app.route('/admin/services/delete/<int:service_id>', methods=['GET', 'POST'])
def admin_delete_service(service_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Check if service exists
    service = execute_query('SELECT * FROM services WHERE id = %s', (service_id,), fetch=True)
    
    if not service:
        flash('Service not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    service = service[0]  # Get the first (and only) service
    
    # Check if service is being used in any appointments
    appointments = execute_query(
        'SELECT COUNT(*) as count FROM appointments WHERE service_id = %s',
        (service_id,),
        fetch=True
    )[0]['count']
    
    if request.method == 'POST':
        if appointments > 0 and 'force_delete' not in request.form:
            flash('This service is associated with appointments. Please confirm deletion.', 'warning')
            return render_template('admin_delete_service.html', service=service, appointments=appointments)
        
        try:
            execute_query('DELETE FROM services WHERE id = %s', (service_id,), commit=True)
            flash('Service deleted successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to delete service: {err}', 'danger')
    
    return render_template('admin_delete_service.html', service=service, appointments=appointments)

# Admin Vehicle Management
@app.route('/admin/vehicles/view/<int:vehicle_id>')
def admin_view_vehicle(vehicle_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get vehicle details
    vehicle = execute_query(
        '''SELECT v.*, u.name as owner_name, u.email as owner_email
           FROM vehicles v 
           JOIN users u ON v.user_id = u.id 
           WHERE v.id = %s''',
        (vehicle_id,),
        fetch=True
    )
    
    if not vehicle:
        flash('Vehicle not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    vehicle = vehicle[0]  # Get the first (and only) vehicle
    
    return render_template('admin_vehicle_details.html', vehicle=vehicle)

@app.route('/admin/vehicles/history/<int:vehicle_id>')
def admin_vehicle_history(vehicle_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get vehicle details
    vehicle = execute_query(
        '''SELECT v.*, u.name as owner_name
           FROM vehicles v 
           JOIN users u ON v.user_id = u.id 
           WHERE v.id = %s''',
        (vehicle_id,),
        fetch=True
    )
    
    if not vehicle:
        flash('Vehicle not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    vehicle = vehicle[0]  # Get the first (and only) vehicle
    
    # Get appointment history
    appointments = execute_query(
        '''SELECT a.*, s.name as service_name, s.price as service_price
           FROM appointments a 
           JOIN services s ON a.service_id = s.id 
           WHERE a.vehicle_id = %s
           ORDER BY a.appointment_date DESC''',
        (vehicle_id,),
        fetch=True
    )
    
    return render_template('admin_vehicle_history.html', vehicle=vehicle, appointments=appointments)

# Admin Customer Management
@app.route('/admin/customers/view/<int:customer_id>')
def admin_view_customer(customer_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get customer details
    customer = execute_query('SELECT * FROM users WHERE id = %s', (customer_id,), fetch=True)
    
    if not customer:
        flash('Customer not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    customer = customer[0]  # Get the first (and only) customer
    
    # Get customer's vehicles
    vehicles = execute_query('SELECT * FROM vehicles WHERE user_id = %s', (customer_id,), fetch=True)
    
    # Get customer's appointments
    appointments = execute_query(
        '''SELECT a.*, s.name as service_name, v.make, v.model 
           FROM appointments a 
           JOIN services s ON a.service_id = s.id 
           JOIN vehicles v ON a.vehicle_id = v.id 
           WHERE a.user_id = %s
           ORDER BY a.appointment_date DESC''',
        (customer_id,),
        fetch=True
    )
    
    return render_template('admin_customer_details.html', customer=customer, vehicles=vehicles, appointments=appointments)

@app.route('/admin/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def admin_edit_customer(customer_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get customer details
    customer = execute_query('SELECT * FROM users WHERE id = %s', (customer_id,), fetch=True)
    
    if not customer:
        flash('Customer not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    customer = customer[0]  # Get the first (and only) customer
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        
        try:
            execute_query(
                'UPDATE users SET name = %s, email = %s, role = %s WHERE id = %s',
                (name, email, role, customer_id),
                commit=True
            )
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('admin_view_customer', customer_id=customer_id))
        except mysql.connector.Error as err:
            flash(f'Failed to update customer: {err}', 'danger')
    
    return render_template('admin_edit_customer.html', customer=customer)

# Admin Product Management
@app.route('/admin/products/add', methods=['GET', 'POST'])
def admin_add_product():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        stock = request.form['stock']
        
        try:
            product_id = execute_query(
                'INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s)',
                (name, description, price, stock),
                commit=True,
                return_last_id=True
            )
            
            # Handle image upload if provided
            if 'product_image' in request.files and request.files['product_image'].filename:
                file = request.files['product_image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Create a unique filename using product ID
                    file_ext = filename.rsplit('.', 1)[1].lower()
                    new_filename = f"product_{product_id}.{file_ext}"
                    
                    # Ensure directory exists
                    os.makedirs('static/images/products', exist_ok=True)
                    
                    # Save the file
                    file_path = os.path.join('static/images/products', new_filename)
                    file.save(file_path)
                    
                    # Update the product with the image URL
                    relative_path = f"images/products/{new_filename}"
                    execute_query(
                        'UPDATE products SET image_url = %s WHERE id = %s',
                        (relative_path, product_id),
                        commit=True
                    )
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to add product: {err}', 'danger')
    
    return render_template('admin_add_product.html')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
def admin_edit_product(product_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get product details
    product = execute_query('SELECT * FROM products WHERE id = %s', (product_id,), fetch=True)
    
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    product = product[0]  # Get the first (and only) product
    
    # Process image URL for display
    if product['image_url']:
        product['image_url'] = url_for('static', filename=product['image_url'])
    else:
        # Default image if none is set
        product['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        stock = request.form['stock']
        
        try:
            execute_query(
                'UPDATE products SET name = %s, description = %s, price = %s, stock = %s WHERE id = %s',
                (name, description, price, stock, product_id),
                commit=True
            )
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to update product: {err}', 'danger')
    
    return render_template('admin_edit_product.html', product=product)

@app.route('/admin/products/delete/<int:product_id>', methods=['GET', 'POST'])
def admin_delete_product(product_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get product details
    product = execute_query('SELECT * FROM products WHERE id = %s', (product_id,), fetch=True)
    
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    product = product[0]  # Get the first (and only) product
    
    # Process image URL for display
    if product['image_url']:
        product['image_url'] = url_for('static', filename=product['image_url'])
    else:
        # Default image if none is set
        product['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    if request.method == 'POST':
        try:
            # Delete the product image if it exists
            if product['image_url'] and product['image_url'] != url_for('static', filename='images/products/default-product.jpg'):
                image_path = os.path.join('static', product['image_url'].replace(url_for('static', filename=''), ''))
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            # Delete the product
            execute_query('DELETE FROM products WHERE id = %s', (product_id,), commit=True)
            flash('Product deleted successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except mysql.connector.Error as err:
            flash(f'Failed to delete product: {err}', 'danger')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    
    return render_template('admin_delete_product.html', product=product)

@app.route('/admin/products/upload-image/<int:product_id>', methods=['GET', 'POST'])
def admin_upload_product_image(product_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get product details
    product = execute_query('SELECT * FROM products WHERE id = %s', (product_id,), fetch=True)
    
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    product = product[0]  # Get the first (and only) product
    
    # Process image URL for display
    if product['image_url']:
        display_url = url_for('static', filename=product['image_url'])
        product['image_url'] = display_url
    else:
        # Default image if none is set
        product['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    if request.method == 'POST':
        if 'product_image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['product_image']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Delete the old image if it exists and it's not the default image
            if product['image_url'] and 'default-product.jpg' not in product['image_url']:
                # Get the original path from the database before URL processing
                old_image = execute_query('SELECT image_url FROM products WHERE id = %s', (product_id,), fetch=True)[0]['image_url']
                if old_image:
                    old_image_path = os.path.join('static', old_image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
            
            # Create a unique filename using product ID
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            new_filename = f"product_{product_id}.{file_ext}"
            
            # Ensure directory exists
            os.makedirs('static/images/products', exist_ok=True)
            
            # Save the file
            file_path = os.path.join('static/images/products', new_filename)
            file.save(file_path)
            
            # Update the product with the new image URL
            relative_path = f"images/products/{new_filename}"
            try:
                execute_query(
                    'UPDATE products SET image_url = %s WHERE id = %s',
                    (relative_path, product_id),
                    commit=True
                )
                flash('Product image updated successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            except mysql.connector.Error as err:
                flash(f'Failed to update product image: {err}', 'danger')
        else:
            flash('Invalid file type. Allowed types: png, jpg, jpeg, gif', 'danger')
    
    return render_template('admin_upload_product_image.html', product=product)

# Shopping Cart Routes
@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('Please login to view your cart', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get cart items with product details
    cart_items = execute_query('''
        SELECT c.id, c.product_id, c.quantity, p.name, p.description, p.price, p.stock, p.image_url,
               (p.price * c.quantity) as subtotal
        FROM cart_items c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    ''', (user_id,), fetch=True)
    
    if cart_items is None:
        flash('Unable to retrieve cart items. Database connection error.', 'danger')
        cart_items = []
    
    # Process image URLs for products
    for item in cart_items:
        if item['image_url']:
            item['image_url'] = url_for('static', filename=item['image_url'])
        else:
            # Default image if none is set
            item['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    # Calculate cart total
    cart_total = sum(item['subtotal'] for item in cart_items) if cart_items else 0
    
    return render_template('cart.html', cart_items=cart_items, cart_total=cart_total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login to add items to your cart', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    quantity = int(request.form.get('quantity', 1))
    
    # Check if product exists and has stock
    product = execute_query('SELECT * FROM products WHERE id = %s', (product_id,), fetch=True)
    
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('products'))
    
    product = product[0]  # Get the first (and only) product
    
    if product['stock'] < quantity:
        flash(f'Sorry, only {product["stock"]} items available in stock', 'warning')
        return redirect(url_for('products'))
    
    try:
        # Check if product is already in cart
        existing_item = execute_query(
            'SELECT * FROM cart_items WHERE user_id = %s AND product_id = %s',
            (user_id, product_id),
            fetch=True
        )
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item[0]['quantity'] + quantity
            if new_quantity > product['stock']:
                new_quantity = product['stock']
                flash(f'Cart updated to maximum available stock ({product["stock"]} items)', 'info')
            
            execute_query(
                'UPDATE cart_items SET quantity = %s WHERE user_id = %s AND product_id = %s',
                (new_quantity, user_id, product_id),
                commit=True
            )
            flash('Cart updated successfully!', 'success')
        else:
            # Add new item to cart
            execute_query(
                'INSERT INTO cart_items (user_id, product_id, quantity) VALUES (%s, %s, %s)',
                (user_id, product_id, quantity),
                commit=True
            )
            flash('Product added to cart!', 'success')
        
        return redirect(url_for('view_cart'))
    except mysql.connector.Error as err:
        flash(f'Failed to add product to cart: {err}', 'danger')
        return redirect(url_for('products'))

@app.route('/cart/update/<int:cart_item_id>', methods=['POST'])
def update_cart_item(cart_item_id):
    if 'user_id' not in session:
        flash('Please login to update your cart', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    quantity = int(request.form.get('quantity', 1))
    
    # Check if cart item exists and belongs to the user
    cart_item = execute_query(
        'SELECT c.*, p.stock FROM cart_items c JOIN products p ON c.product_id = p.id WHERE c.id = %s AND c.user_id = %s',
        (cart_item_id, user_id),
        fetch=True
    )
    
    if not cart_item:
        flash('Cart item not found', 'danger')
        return redirect(url_for('view_cart'))
    
    cart_item = cart_item[0]  # Get the first (and only) cart item
    
    # Validate quantity
    if quantity <= 0:
        # Remove item if quantity is 0 or negative
        execute_query('DELETE FROM cart_items WHERE id = %s', (cart_item_id,), commit=True)
        flash('Item removed from cart', 'success')
    else:
        # Check stock availability
        if quantity > cart_item['stock']:
            quantity = cart_item['stock']
            flash(f'Quantity adjusted to maximum available stock ({cart_item["stock"]} items)', 'info')
        
        # Update quantity
        execute_query(
            'UPDATE cart_items SET quantity = %s WHERE id = %s',
            (quantity, cart_item_id),
            commit=True
        )
        flash('Cart updated successfully!', 'success')
    
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<int:cart_item_id>')
def remove_from_cart(cart_item_id):
    if 'user_id' not in session:
        flash('Please login to manage your cart', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Check if cart item exists and belongs to the user
    cart_item = execute_query(
        'SELECT * FROM cart_items WHERE id = %s AND user_id = %s',
        (cart_item_id, user_id),
        fetch=True
    )
    
    if not cart_item:
        flash('Cart item not found', 'danger')
        return redirect(url_for('view_cart'))
    
    # Remove the item
    execute_query('DELETE FROM cart_items WHERE id = %s', (cart_item_id,), commit=True)
    flash('Item removed from cart', 'success')
    
    return redirect(url_for('view_cart'))

@app.route('/cart/clear')
def clear_cart():
    if 'user_id' not in session:
        flash('Please login to manage your cart', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Remove all items from the user's cart
    execute_query('DELETE FROM cart_items WHERE user_id = %s', (user_id,), commit=True)
    flash('Cart cleared successfully!', 'success')
    
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please login to checkout', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get user information
    user = execute_query('SELECT * FROM users WHERE id = %s', (user_id,), fetch=True)
    if not user:
        flash('User information not found', 'danger')
        return redirect(url_for('view_cart'))
    
    user = user[0]
    
    # Get cart items with product details
    cart_items = execute_query('''
        SELECT c.id, c.product_id, c.quantity, p.name, p.description, p.price, p.stock, p.image_url,
               (p.price * c.quantity) as subtotal
        FROM cart_items c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    ''', (user_id,), fetch=True)
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('products'))
    
    # Calculate cart total
    cart_total = sum(item['subtotal'] for item in cart_items)
    
    if request.method == 'POST':
        # Get form data
        delivery_address = request.form.get('delivery_address')
        contact_phone = request.form.get('contact_phone')
        payment_method = request.form.get('payment_method')
        
        # Validate form data
        if not delivery_address or not contact_phone or not payment_method:
            flash('Please fill in all required fields', 'danger')
            return render_template('checkout.html', cart_items=cart_items, cart_total=cart_total, user=user)
        
        # Check if payment method is valid
        valid_payment_methods = ['cash_on_delivery', 'upi', 'credit_card', 'debit_card']
        if payment_method not in valid_payment_methods:
            flash('Invalid payment method', 'danger')
            return render_template('checkout.html', cart_items=cart_items, cart_total=cart_total, user=user)
        
        # Create order
        try:
            # Start with UPI transaction ID as None
            upi_transaction_id = None
            
            # If payment method is UPI, get transaction ID
            if payment_method == 'upi':
                upi_transaction_id = request.form.get('upi_transaction_id')
                if not upi_transaction_id:
                    flash('UPI Transaction ID is required for UPI payments', 'danger')
                    return render_template('checkout.html', cart_items=cart_items, cart_total=cart_total, user=user)
            
            # Insert order into database
            order_id = execute_query(
                '''INSERT INTO orders 
                   (user_id, total_amount, payment_method, payment_status, delivery_address, contact_phone, upi_transaction_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (user_id, cart_total, payment_method, 
                 'paid' if payment_method == 'upi' else 'pending', 
                 delivery_address, contact_phone, upi_transaction_id),
                commit=True,
                return_last_id=True
            )
            
            # Insert order items
            for item in cart_items:
                execute_query(
                    '''INSERT INTO order_items 
                       (order_id, product_id, quantity, price_per_unit, subtotal)
                       VALUES (%s, %s, %s, %s, %s)''',
                    (order_id, item['product_id'], item['quantity'], item['price'], item['subtotal']),
                    commit=True
                )
                
                # Update product stock
                execute_query(
                    'UPDATE products SET stock = stock - %s WHERE id = %s',
                    (item['quantity'], item['product_id']),
                    commit=True
                )
            
            # Clear the cart
            execute_query('DELETE FROM cart_items WHERE user_id = %s', (user_id,), commit=True)
            
            # Redirect to order confirmation page
            flash('Order placed successfully!', 'success')
            return redirect(url_for('order_confirmation', order_id=order_id))
            
        except mysql.connector.Error as err:
            flash(f'Failed to place order: {err}', 'danger')
            return render_template('checkout.html', cart_items=cart_items, cart_total=cart_total, user=user)
    
    return render_template('checkout.html', cart_items=cart_items, cart_total=cart_total, user=user)

@app.route('/order/confirmation/<int:order_id>')
def order_confirmation(order_id):
    if 'user_id' not in session:
        flash('Please login to view order confirmation', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get order details
    order = execute_query(
        '''SELECT o.*, u.name as customer_name, u.email as customer_email
           FROM orders o
           JOIN users u ON o.user_id = u.id
           WHERE o.id = %s AND o.user_id = %s''',
        (order_id, user_id),
        fetch=True
    )
    
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('dashboard'))
    
    order = order[0]
    
    # Get order items
    order_items = execute_query(
        '''SELECT oi.*, p.name, p.image_url
           FROM order_items oi
           JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = %s''',
        (order_id,),
        fetch=True
    )
    
    # Process image URLs for products
    for item in order_items:
        if item['image_url']:
            item['image_url'] = url_for('static', filename=item['image_url'])
        else:
            # Default image if none is set
            item['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    return render_template('order_confirmation.html', order=order, order_items=order_items)

@app.route('/orders')
def view_orders():
    if 'user_id' not in session:
        flash('Please login to view your orders', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get all orders for the user
    orders = execute_query(
        '''SELECT o.*, COUNT(oi.id) as item_count
           FROM orders o
           JOIN order_items oi ON o.id = oi.order_id
           WHERE o.user_id = %s
           GROUP BY o.id
           ORDER BY o.created_at DESC''',
        (user_id,),
        fetch=True
    )
    
    if orders is None:
        flash('Unable to retrieve orders. Database connection error.', 'danger')
        orders = []
    
    return render_template('orders.html', orders=orders)

@app.route('/orders/<int:order_id>')
def view_order_details(order_id):
    if 'user_id' not in session:
        flash('Please login to view order details', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get order details
    order = execute_query(
        '''SELECT o.*, u.name as customer_name, u.email as customer_email
           FROM orders o
           JOIN users u ON o.user_id = u.id
           WHERE o.id = %s AND (o.user_id = %s OR %s = (SELECT id FROM users WHERE role = 'admin' AND id = %s))''',
        (order_id, user_id, user_id, user_id),
        fetch=True
    )
    
    if not order:
        flash('Order not found or you do not have permission to view it', 'danger')
        return redirect(url_for('view_orders'))
    
    order = order[0]
    
    # Get order items
    order_items = execute_query(
        '''SELECT oi.*, p.name, p.image_url
           FROM order_items oi
           JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = %s''',
        (order_id,),
        fetch=True
    )
    
    # Process image URLs for products
    for item in order_items:
        if item['image_url']:
            item['image_url'] = url_for('static', filename=item['image_url'])
        else:
            # Default image if none is set
            item['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    return render_template('order_details.html', order=order, order_items=order_items)

@app.route('/admin/orders')
def admin_view_orders():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get all orders
    orders = execute_query(
        '''SELECT o.*, u.name as customer_name, u.email as customer_email, COUNT(oi.id) as item_count
           FROM orders o
           JOIN users u ON o.user_id = u.id
           JOIN order_items oi ON o.id = oi.order_id
           GROUP BY o.id
           ORDER BY o.created_at DESC''',
        fetch=True
    )
    
    if orders is None:
        flash('Unable to retrieve orders. Database connection error.', 'danger')
        orders = []
    
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>')
def admin_view_order_details(order_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    # Get order details
    order = execute_query(
        '''SELECT o.*, u.name as customer_name, u.email as customer_email
           FROM orders o
           JOIN users u ON o.user_id = u.id
           WHERE o.id = %s''',
        (order_id,),
        fetch=True
    )
    
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('admin_view_orders'))
    
    order = order[0]
    
    # Get order items
    order_items = execute_query(
        '''SELECT oi.*, p.name, p.image_url
           FROM order_items oi
           JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = %s''',
        (order_id,),
        fetch=True
    )
    
    # Process image URLs for products
    for item in order_items:
        if item['image_url']:
            item['image_url'] = url_for('static', filename=item['image_url'])
        else:
            # Default image if none is set
            item['image_url'] = url_for('static', filename='images/products/default-product.jpg')
    
    return render_template('admin_order_details.html', order=order, order_items=order_items)

@app.route('/admin/orders/update-status/<int:order_id>', methods=['POST'])
def admin_update_order_status(order_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    order_status = request.form.get('order_status')
    payment_status = request.form.get('payment_status')
    
    valid_order_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    valid_payment_statuses = ['pending', 'paid', 'failed', 'refunded']
    
    if order_status and order_status in valid_order_statuses:
        execute_query(
            'UPDATE orders SET order_status = %s WHERE id = %s',
            (order_status, order_id),
            commit=True
        )
        flash('Order status updated successfully!', 'success')
    
    if payment_status and payment_status in valid_payment_statuses:
        execute_query(
            'UPDATE orders SET payment_status = %s WHERE id = %s',
            (payment_status, order_id),
            commit=True
        )
        flash('Payment status updated successfully!', 'success')
    
    return redirect(url_for('admin_view_order_details', order_id=order_id))

if __name__ == '__main__':
    app.run(debug=config.DEBUG) 