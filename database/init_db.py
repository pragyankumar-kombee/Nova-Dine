from sqlalchemy import create_engine, text
import sys
import os

# Database name to create
DB_NAME = "kombee_hackathon"
# Using what seems to be the working password
URL_POSTGRES = "postgresql://postgres:admin123@localhost:5432/postgres"

try:
    print(f"Connecting to default 'postgres' database...")
    engine = create_engine(URL_POSTGRES, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        # Check if database exists
        check_query = f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'"
        result = connection.execute(text(check_query))
        
        if not result.fetchone():
            print(f"Database '{DB_NAME}' not found. Creating...")
            connection.execute(text(f"CREATE DATABASE {DB_NAME}"))
            print(f"Database '{DB_NAME}' created successfully.")
        else:
            print(f"Database '{DB_NAME}' already exists.")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
