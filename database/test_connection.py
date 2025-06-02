from connection import get_db_connection, close_connection, execute_query

def test_database_connection():
    """
    Test the database connection and perform basic queries.
    """
    print("Testing database connection...")
    
    # Test basic connection
    connection = get_db_connection()
    if connection and connection.is_connected():
        print("✅ Successfully connected to MySQL database")
        close_connection(connection)
    else:
        print("❌ Failed to connect to MySQL database")
        return
    
    # Test execute_query function with a simple SELECT
    print("\nTesting execute_query with SELECT...")
    try:
        users = execute_query("SELECT id, name, email, role FROM users LIMIT 3", fetch=True)
        if users:
            print(f"✅ Successfully retrieved {len(users)} users:")
            for user in users:
                print(f"  - {user['name']} ({user['email']}) - {user['role']}")
        else:
            print("❌ No users found or query failed")
    except Exception as e:
        print(f"❌ Error executing SELECT query: {e}")
    
    # Test if tables exist
    print("\nChecking if required tables exist...")
    tables = ["users", "vehicles", "services", "appointments", "products", "invoices", "invoice_items"]
    
    for table in tables:
        try:
            result = execute_query(f"SELECT 1 FROM {table} LIMIT 1", fetch=True)
            if result is not None:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' may not exist or is empty")
        except Exception as e:
            print(f"❌ Error checking table '{table}': {e}")

if __name__ == "__main__":
    test_database_connection() 