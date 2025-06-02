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
        
        if user and len(user) > 0 and check_password_hash(user[0]['password'], password):
            user = user[0]  # Get the first (and only) user
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = 'customer'  # Default role
        
        hashed_password = generate_password_hash(password)
        
        try:
            execute_query(
                'INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)',
                (name, email, hashed_password, role),
                commit=True
            )
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
    
    # Get appointments
    appointments = execute_query('''
        SELECT a.*, u.name as customer_name, s.name as service_name, v.make, v.model 
        FROM appointments a 
        JOIN users u ON a.user_id = u.id 
        JOIN services s ON a.service_id = s.id
        JOIN vehicles v ON a.vehicle_id = v.id
        ORDER BY a.appointment_date DESC
    ''', fetch=True)
    
    # Get vehicles
    vehicles = execute_query('''
        SELECT v.*, u.name as owner_name 
        FROM vehicles v 
        JOIN users u ON v.user_id = u.id
    ''', fetch=True)
    
    # Get customers
    customers = execute_query('''
        SELECT u.*, 
            (SELECT COUNT(*) FROM vehicles WHERE user_id = u.id) as vehicle_count,
            (SELECT COUNT(*) FROM appointments WHERE user_id = u.id) as appointment_count
        FROM users u
        WHERE u.role = 'customer'
        ORDER BY u.name
    ''', fetch=True)
    
    # Get products
    products = execute_query('SELECT * FROM products ORDER BY name', fetch=True)
    
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
    
    # Get user's appointments
    appointments = execute_query('''
        SELECT a.*, s.name as service_name, v.make, v.model 
        FROM appointments a 
        JOIN services s ON a.service_id = s.id 
        JOIN vehicles v ON a.vehicle_id = v.id 
        WHERE a.user_id = %s
        ORDER BY a.appointment_date DESC
    ''', (user_id,), fetch=True)
    
    # Get available services
    services = execute_query('SELECT * FROM services', fetch=True)
    
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

if __name__ == '__main__':
    app.run(debug=config.DEBUG) 