import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from faker import Faker
from app.api import create_app
from app.api.extensions import db
from database.models import User, Product, InventoryTransaction, Order
import random
from datetime import datetime, timedelta

fake = Faker()
app = create_app()

def seed_data():
    with app.app_context():
        # Clean existing
        db.drop_all()
        db.create_all()
        
        # Create user
        user = User(name="Chef Mario", restaurant_name="Mario's Bistro", email="chef@mario.com")
        db.session.add(user)
        
        # Create products
        ingredients = ["Chicken", "Onion", "Tomato", "Rice", "Butter", "Paneer", "Milk", "Salt", "Pepper"]
        products = []
        for name in ingredients:
            p = Product(
                name=name,
                category="Dairy" if name in ["Milk", "Butter", "Paneer"] else "Vegetable" if name in ["Onion", "Tomato"] else "Meat" if name == "Chicken" else "Pantry",
                unit="kg" if name != "Milk" else "L",
                current_stock=random.uniform(2, 20),
                min_stock_threshold=10.0,
                price=random.uniform(20, 500)
            )
            db.session.add(p)
            products.append(p)
        
        db.session.flush()
        
        # Create historical transactions (30 days)
        for p in products:
            for i in range(30):
                date = datetime.utcnow() - timedelta(days=i)
                # Daily usage
                db.session.add(InventoryTransaction(
                    product_id=p.id,
                    transaction_type="used",
                    quantity=random.uniform(0.5, 3.0),
                    timestamp=date
                ))
        
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    seed_data()
