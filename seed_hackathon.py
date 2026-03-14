import os
import random
import time
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from faker import Faker

load_dotenv()
fake = Faker()

def seed_database():
    db_url = os.getenv('DATABASE_URL')
    print(f"Connecting to database...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print("Cleaning existing data...")
    cur.execute("TRUNCATE users, products, orders, order_details, menu_documents RESTART IDENTITY CASCADE")
    conn.commit()

    # 1. Create 10 Users
    print("Generating 10 users...")
    users = []
    for i in range(10):
        users.append((
            f"user_{i+1}",
            fake.email(),
            fake.company() + " Restaurant",
            datetime.utcnow()
        ))
    
    execute_values(cur, "INSERT INTO users (username, email, restaurant_name, created_at) VALUES %s RETURNING id", users)
    user_ids = [r[0] for r in cur.fetchall()]
    conn.commit()

    # 2. Create 50,000 Products
    print("Generating 50,000 products (this may take a minute)...")
    categories = ['Vegetables', 'Fruits', 'Meat', 'Dairy', 'Grains', 'Spices', 'Beverages', 'Bakery', 'Frozen', 'Canned']
    units = ['kg', 'g', 'liters', 'pieces', 'packs', 'boxes']
    
    products = []
    # Seed with some common commodities first to ensure matches
    common_commodities = [
        'Tomato', 'Onion', 'Potato', 'Garlic', 'Chicken Breast', 'Eggs', 'Butter', 'Milk', 
        'Basmati Rice', 'Flour', 'Salt', 'Olive Oil', 'Bell Pepper', 'Mozzarella Cheese', 
        'Black Pepper', 'Paneer', 'Chicken Wings', 'Spring Rolls', 'Spaghetti', 'Mango', 
        'Coffee', 'Green Tea', 'Ice', 'Bread', 'Cream', 'Cucumber'
    ]
    
    for name in common_commodities:
        products.append((
            name,
            random.choice(categories),
            random.choice(units),
            random.uniform(5, 100),
            random.uniform(10, 30),
            fake.company()
        ))

    # Fill up to 50k
    for i in range(len(common_commodities), 50000):
        products.append((
            fake.word().capitalize() + " " + fake.word(),
            random.choice(categories),
            random.choice(units),
            random.uniform(0, 500), # stock
            random.uniform(10, 50), # reorder level
            fake.company()
        ))
    
    execute_values(cur, "INSERT INTO products (name, category, unit, current_stock, reorder_level, supplier) VALUES %s RETURNING id", products)
    product_ids = [r[0] for r in cur.fetchall()]
    conn.commit()

    # 3. Create 20,000 Orders (2,000 per user)
    print("Generating 20,000 orders...")
    orders = []
    for u_id in user_ids:
        for _ in range(2000):
            # Orders spread over the last 180 days
            order_date = datetime.utcnow() - timedelta(days=random.randint(0, 180), hours=random.randint(0, 23))
            orders.append((
                u_id,
                order_date,
                random.uniform(50, 1000)
            ))
    
    execute_values(cur, "INSERT INTO orders (user_id, order_date, total_amount) VALUES %s RETURNING id", orders)
    order_ids = [r[0] for r in cur.fetchall()]
    conn.commit()

    # 4. Create OrderDetails (5 to 15 entries per order)
    # Total entries will be ~200,000
    print("Generating Order Details (~200,000 entries)...")
    details = []
    
    # To make predictions work, let's make certain products popular for users
    user_favorites = {u_id: random.sample(product_ids[:100], 20) for u_id in user_ids}

    for o_id in order_ids:
        # Get user_id for this order (simplified for speed)
        # We'll just pick favorite products based on some randomness
        num_items = random.randint(5, 15)
        
        # Pick from a small subset of "frequent" products to make historical patterns detectable
        selected_p_ids = random.sample(product_ids[:200], num_items)
        
        for p_id in selected_p_ids:
            details.append((
                o_id,
                p_id,
                random.uniform(0.5, 10.0) # quantity
            ))
            
            # Batch inserts to avoid memory issues
            if len(details) >= 10000:
                execute_values(cur, "INSERT INTO order_details (order_id, product_id, quantity) VALUES %s", details)
                details = []
    
    if details:
        execute_values(cur, "INSERT INTO order_details (order_id, product_id, quantity) VALUES %s", details)
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"Finished seeding: 10 Users, 50,000 Products, 20,000 Orders.")

if __name__ == "__main__":
    start_time = time.time()
    seed_database()
    print(f"Total time: {time.time() - start_time:.2f} seconds")
