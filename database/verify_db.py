from sqlalchemy import create_engine, text
import sys
import os

# Add the project root to sys.path to import settings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config.settings import settings
    print(f"Attempting to connect to: {settings.database_url}")
    
    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print(f"Connection Successful: {result.fetchone()}")

except Exception as e:
    print(f"Connection Failed: {e}")
    sys.exit(1)
