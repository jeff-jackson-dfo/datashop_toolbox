import psycopg2
from psycopg2 import OperationalError

def mardid_django_postgresql_db_connection():
    try:
        conn = psycopg2.connect(
        host="vm-bio-mar-did-2",
        database="production_db",
        user="dbadmin",
        password="dj-mar!25*",
        port=5432,
        connect_timeout=5
        )
 
        if conn.status == psycopg2.extensions.STATUS_READY:
            print("✅ Database connection successful!")
        else:
            print("⚠️ Connected, but connection not ready.")
 
        return conn
 
    except OperationalError as e:
        print("❌ Database connection failed.")
        print("Error:", e)
        return None
 
    except Exception as e:
        print("❌ Unexpected error occurred.")
        print("Error:", e)
        return None

def main():
    conn = mardid_django_postgresql_db_connection()
    if conn:
        conn.close()

if __name__ == "__main__":
    main()
