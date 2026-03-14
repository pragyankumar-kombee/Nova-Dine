from sqlalchemy import create_engine, text
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test connection to default 'postgres' database first
url = "postgresql://postgres:admiin123@localhost:5432/postgres"

try:
    print(f"Testing credentials on default 'postgres' DB...")
    engine = create_engine(url)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print(f"Credentials Verified! Found: {result.fetchone()}")
        
    # Now check if the target DB exists
    print(f"Checking if 'kombee_hackathon' exists...")
    with engine.connect() as connection:
        res = connection.execute(text("SELECT 1 FROM pg_database WHERE datname='kombee_hackathon'"))
        if not res.fetchone():
            print("Database 'kombee_hackathon' DOES NOT EXIST. Creating it...")
            connection.execute(text("COMMIT")) # End transaction
            connection.execute(text("CREATE DATABASE kombee_hackathon"))
            print("Database created.")
        else:
            print("Database 'kombee_hackathon' exists.")

except Exception as e:
    print(f"Operation Failed: {e}")
    sys.exit(1)
