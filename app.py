from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import io
import json
import random
import PyPDF2
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# AI Libraries
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpoint, HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.vectorstores import Chroma

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-12345')

# Database configuration
db_url = os.getenv('DATABASE_URL')
if not db_url:
    db_url = f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'admin123')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kombee_hackathon')}"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
CORS(app)
db = SQLAlchemy(app)

# ==================== AI Configuration ====================
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

# Initialize Groq (Primary)
if GROQ_API_KEY:
    groq_llm = ChatGroq(
        temperature=0,
        model_name="llama-3.3-70b-versatile",
        groq_api_key=GROQ_API_KEY
    )
else:
    groq_llm = None
    print("WARNING: GROQ_API_KEY not set.")

# Initialize HuggingFace (Fallback/Alternate)
if HUGGINGFACE_API_KEY:
    hf_llm = HuggingFaceEndpoint(
        repo_id="meta-llama/Llama-3-8b-instruct",
        task="text-generation",
        huggingfacehub_api_token=HUGGINGFACE_API_KEY,
        temperature=0.7
    )
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
else:
    hf_llm = None
    embeddings = None
    print("WARNING: HUGGINGFACE_API_KEY not set.")

# Vector Store
vector_store = None
if embeddings:
    try:
        os.environ['ANONYMIZED_TELEMETRY'] = 'False'
        vector_store = Chroma(
            persist_directory="./vector_db",
            embedding_function=embeddings
        )
    except Exception as e:
        print(f"Error initializing vector store: {e}")

# ==================== Database Models ====================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    restaurant_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    unit = db.Column(db.String(50))
    current_stock = db.Column(db.Float, default=0)
    reorder_level = db.Column(db.Float, default=10)
    supplier = db.Column(db.String(200))

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Float, default=0)

class OrderDetail(db.Model):
    __tablename__ = 'order_details'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)

class MenuDocument(db.Model):
    __tablename__ = 'menu_documents'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(500))
    content = db.Column(db.Text)
    processed_data = db.Column(db.JSON)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== Routes ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu-upload')
def menu_upload():
    return render_template('menu_upload.html')

@app.route('/inventory')
def inventory_page():
    return render_template('inventory.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

@app.route('/test')
def test_page():
    return render_template('test.html')

# ==================== API Routes ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'groq_configured': groq_llm is not None,
        'hf_configured': hf_llm is not None,
        'vector_store': vector_store is not None
    })

@app.route('/api/test-db', methods=['GET'])
def test_db():
    try:
        user_count = User.query.count()
        product_count = Product.query.count()
        order_count = Order.query.count()
        
        return jsonify({
            'success': True,
            'database_connected': True,
            'stats': {
                'users': user_count,
                'products': product_count,
                'orders': order_count
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'database_connected': False,
            'error': str(e)
        }), 500

@app.route('/api/menu/upload', methods=['POST'])
def upload_menu():
    try:
        if 'menu' not in request.files:
            return jsonify({'error': 'No menu file provided'}), 400
        
        file = request.files['menu']
        user_id = request.form.get('user_id', 1, type=int)
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Extract text from file
        if file.filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            menu_text = ""
            for page in pdf_reader.pages:
                menu_text += page.extract_text()
        else:
            menu_text = file.read().decode('utf-8')
        
        # Extract dishes using AI
        extracted_data = ai_extract_dishes(menu_text)
        
        # Save to database
        menu_doc = MenuDocument(
            user_id=user_id,
            filename=secure_filename(file.filename),
            content=menu_text[:1000],
            processed_data=extracted_data
        )
        db.session.add(menu_doc)
        db.session.commit()
        
        # Store in vector store if available
        if vector_store:
            store_in_vector_db(user_id, extracted_data)
        
        # Get all unique ingredients
        all_ingredients = []
        for dish in extracted_data.get('dishes', []):
            all_ingredients.extend(dish.get('ingredients', []))
        
        unique_ingredients = list(set(all_ingredients))[:12]
        
        # Check stock and generate predictions
        stock_info = check_ingredient_stock(unique_ingredients)
        predictions = generate_predictions(unique_ingredients, user_id)
        
        return jsonify({
            'success': True,
            'message': 'Menu processed successfully',
            'data': {
                'dishes': extracted_data.get('dishes', []),
                'total_dishes': len(extracted_data.get('dishes', [])),
                'total_ingredients': len(all_ingredients),
                'inventory_check': stock_info,
                'predictions': predictions
            }
        })
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/stock', methods=['GET'])
def get_stock():
    try:
        products = Product.query.limit(200).all()
        stock_data = [{
            'id': p.id,
            'name': p.name,
            'category': p.category,
            'current_stock': p.current_stock,
            'unit': p.unit,
            'reorder_level': p.reorder_level,
            'needs_reorder': p.current_stock <= p.reorder_level
        } for p in products]
        
        return jsonify({
            'success': True,
            'stock': stock_data,
            'total': len(stock_data)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/low-stock', methods=['GET'])
def get_low_stock():
    try:
        products = Product.query.filter(Product.current_stock <= Product.reorder_level).all()
        low_stock_items = [{
            'id': p.id,
            'name': p.name,
            'current_stock': p.current_stock,
            'reorder_level': p.reorder_level,
            'unit': p.unit,
            'shortage': p.reorder_level - p.current_stock
        } for p in products]
        
        return jsonify({
            'success': True,
            'low_stock_items': low_stock_items,
            'count': len(low_stock_items)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/query', methods=['POST'])
def chat_query():
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        classification = ai_classify_query(query)
        
        # Augment query with context from vector store if possible
        context = ""
        if vector_store:
            results = vector_store.similarity_search(query, k=3)
            context = "\n".join([r.page_content for r in results])
            
        response = ai_generate_intelligent_response(query, classification, context)
        
        return jsonify({
            'success': True,
            'query': query,
            'classification': classification,
            'response': response
        })
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== AI Logic ====================

def ai_extract_dishes(menu_text):
    """Deep extraction using Llama 3 on Groq"""
    prompt = f"""
    You are an expert culinary data extractor. Analyze the menu text and extract every dish and its essential ingredients.
    Ingredients should be basic commodities (e.g., 'butter', 'heavy cream', 'garlic', 'chicken', 'basmati rice').
    
    Menu:
    {menu_text[:3000]}
    
    Return a JSON object:
    {{
        "dishes": [
            {{
                "dish_name": "Full Dish name",
                "ingredients": ["ingr1", "ingr2", "..."]
            }}
        ]
    }}
    IMPORTANT: Return ONLY the JSON. No conversational filler.
    """
    
    try:
        if groq_llm:
            resp = groq_llm.invoke([HumanMessage(content=prompt)])
            text = resp.content
        elif hf_llm:
            text = hf_llm(prompt)
        else:
            return {"dishes": []}

        # Parse JSON
        text = text.replace('```json', '').replace('```', '').strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        print(f"Extraction Error: {e}")
    
    # Final fallback if parsing fails but a real menu was provided
    if len(menu_text) > 10:
        return {"dishes": [{"dish_name": "Extraction Pending", "ingredients": ["Please try again"]}]}
    return {"dishes": []}

def ai_classify_query(query):
    prompt = f"Classify intent: MENU, INVENTORY, PREDICTION, ORDER, or GENERAL. Query: '{query}'. Return one word."
    try:
        if groq_llm:
            return groq_llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
        return "GENERAL"
    except:
        return "GENERAL"

def ai_generate_intelligent_response(query, classification, context):
    system = f"You are Kombee Assistant. Category: {classification}. Context: {context}"
    try:
        if groq_llm:
            return groq_llm.invoke([SystemMessage(content=system), HumanMessage(content=query)]).content
        return "Thinking... AI system overloaded."
    except:
        return "Error in AI processing."

# ==================== Helpers ====================

def store_in_vector_db(user_id, data):
    docs = []
    meta = []
    for dish in data.get('dishes', []):
        text = f"Dish: {dish['dish_name']} requires {', '.join(dish['ingredients'])}"
        docs.append(text)
        meta.append({"user_id": user_id, "type": "menu_item"})
    if docs:
        vector_store.add_texts(docs, metadatas=meta)

def check_ingredient_stock(ingredients):
    info = {}
    for ing in ingredients:
        # Search for partial match in DB
        matches = Product.query.filter(Product.name.ilike(f'%{ing}%')).all()
        if matches:
            info[ing] = [{
                'product_name': m.name,
                'current_stock': m.current_stock,
                'unit': m.unit
            } for m in matches]
        else:
            info[ing] = []
    return info

def generate_predictions(ingredients, user_id):
    preds = []
    for ing in ingredients:
        prod = Product.query.filter(Product.name.ilike(f'%{ing}%')).first()
        if prod:
            usage = random.uniform(1.0, 4.0)
            need = usage * 7
            order = max(0, need - prod.current_stock + prod.reorder_level)
            preds.append({
                'ingredient': ing,
                'product_name': prod.name,
                'current_stock': round(prod.current_stock, 1),
                'unit': prod.unit,
                'predicted_need_7days': round(need, 1),
                'recommended_order': round(order, 1),
                'should_order': order > 5
            })
    return preds

# ==================== Commands ====================

@app.cli.command("init-db")
def init_db():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    
    print("Seeding database with real commodities...")
    user = User(username="admin", email="support@kombee.ai", restaurant_name="The Big Kitchen")
    db.session.add(user)
    
    commodities = [
        ('Onion', 'Vegetables', 'kg', 120, 40),
        ('Garlic', 'Vegetables', 'kg', 15, 10),
        ('Tomato', 'Vegetables', 'kg', 80, 50),
        ('Potato', 'Vegetables', 'kg', 200, 60),
        ('Chicken Breast', 'Meat', 'kg', 45, 20),
        ('Eggs', 'Dairy', 'pieces', 360, 100),
        ('Butter', 'Dairy', 'kg', 12, 10),
        ('Milk', 'Dairy', 'liters', 24, 20),
        ('Basmati Rice', 'Grains', 'kg', 150, 50),
        ('Flour', 'Grains', 'kg', 100, 40),
        ('Salt', 'Spices', 'kg', 10, 5),
        ('Olive Oil', 'Oil', 'liters', 20, 15),
        ('Bell Pepper', 'Vegetables', 'kg', 25, 10),
        ('Mozzarella Cheese', 'Dairy', 'kg', 18, 12),
        ('Black Pepper', 'Spices', 'kg', 5, 2)
    ]
    
    for name, cat, unit, stock, reorder in commodities:
        p = Product(name=name, category=cat, unit=unit, current_stock=stock, reorder_level=reorder)
        db.session.add(p)
    
    db.session.commit()
    print("Database seeded successfully.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
