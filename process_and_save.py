import os
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# Database Config
db_url = os.getenv('DATABASE_URL')
if not db_url:
    db_url = f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'admin123')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kombee_hackathon')}"

engine = create_engine(db_url)

# AI Config
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
llm = ChatGroq(
    temperature=0.3,
    model_name="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY
)

def process_and_save():
    print("--- AI Processing Started ---")
    
    # Task: Get a relevant answer about inventory optimization
    query = "What are the top 3 ingredients I should prioritize for reordering based on typical restaurant demand, and why?"
    
    try:
        # Use AI to get a relevant answer
        system_msg = "You are an expert supply chain optimizer for restaurants. Provide a concise JSON response."
        human_msg = f"Analyze this request: {query}. Return a JSON with 'priorities' (list of objects with 'item', 'reason') and a 'summary' string."
        
        print(f"Querying AI: {query}...")
        response = llm.invoke([SystemMessage(content=system_msg), HumanMessage(content=human_msg)])
        ai_text = response.content
        
        # Clean and Parse JSON
        clean_json = ai_text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_json)
        
        print("AI Response Received Successfully!")
        
        # Save to Database (Native SQL to be sure it works regardless of models)
        with engine.connect() as conn:
            # Create table if not exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_insights (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    classification VARCHAR(50),
                    response_json JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("COMMIT"))
            
            # Insert the data
            insert_query = text("""
                INSERT INTO ai_insights (query, classification, response_json)
                VALUES (:query, :classification, :response_json)
                RETURNING id
            """)
            result = conn.execute(insert_query, {
                "query": query,
                "classification": "INVENTORY_ADVICE",
                "response_json": json.dumps(data)
            })
            new_id = result.fetchone()[0]
            conn.execute(text("COMMIT"))
            
        print(f"Data saved to database in table 'ai_insights' with ID: {new_id}")
        
        # Output in "Database Format" (SQL Insert)
        print("\n--- DATABASE FORMAT (SQL) ---")
        sql_insert = f"INSERT INTO ai_insights (query, classification, response_json)\nVALUES ('{query}', 'INVENTORY_ADVICE', '{json.dumps(data)}');"
        print(sql_insert)
        
        # Command to execute in pgAdmin
        print("\n--- PGADMIN EXECUTION COMMAND ---")
        print("To see your data in pgAdmin, open the Query Tool and run:")
        print("SELECT * FROM ai_insights ORDER BY created_at DESC LIMIT 1;")
        
        return data

    except Exception as e:
        print(f"Error during AI processing: {e}")
        return None

if __name__ == "__main__":
    process_and_save()
