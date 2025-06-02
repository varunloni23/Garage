from database.connection import execute_query
from werkzeug.security import check_password_hash

def test_db_connection():
    print("Testing database connection...")
    try:
        # Test basic query
        result = execute_query("SELECT 1", fetch=True)
        if result:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

def test_users_table():
    print("\nTesting users table...")
    try:
        users = execute_query("SELECT * FROM users LIMIT 5", fetch=True)
        if users:
            print(f"✅ Found {len(users)} users in database")
            for user in users:
                print(f"  - ID: {user['id']}, Name: {user['name']}, Email: {user['email']}, Role: {user['role']}")
        else:
            print("❌ No users found or users table doesn't exist")
    except Exception as e:
        print(f"❌ Error querying users table: {e}")

def test_login(email, password):
    print(f"\nTesting login with {email}...")
    try:
        user = execute_query('SELECT * FROM users WHERE email = %s', (email,), fetch=True)
        
        if user and len(user) > 0:
            print(f"✅ Found user with email {email}")
            user = user[0]  # Get the first user
            
            if check_password_hash(user['password'], password):
                print("✅ Password verification successful")
            else:
                print("❌ Password verification failed")
        else:
            print(f"❌ No user found with email {email}")
    except Exception as e:
        print(f"❌ Error testing login: {e}")

if __name__ == "__main__":
    test_db_connection()
    test_users_table()
    
    # Test admin login
    test_login('admin@garage.com', 'admin123')
    
    # Test a customer login
    test_login('john@example.com', 'password123') 