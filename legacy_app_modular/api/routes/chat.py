from flask import Blueprint, request, jsonify
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import settings

chat_bp = Blueprint('chat', __name__)

# Initialize Groq
groq_api_key = os.getenv('GROQ_API_KEY') or settings.groq_api_key
model = ChatGroq(
    temperature=0,
    model_name="llama3-70b-8192",
    groq_api_key=groq_api_key
)

# Orchestrator prompts
prompt_path = 'config/prompts/classifier_prompt.txt'
if os.path.exists(prompt_path):
    with open(prompt_path, 'r') as f:
        CLASSIFIER_PROMPT = f.read()
else:
    CLASSIFIER_PROMPT = "Classify this query as MENU_UPLOAD, INVENTORY_CHECK, ORDER_PREDICTION, or GENERAL: '{query}'. Return ONLY the category name."

@chat_bp.route('/query', methods=['POST'])
def handle_query():
    """Handle chat queries with orchestration"""
    data = request.get_json()
    query = data.get('query', '')
    user_id = data.get('user_id', 1)
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        # Step 1: Classify the query
        classification = classify_query(query)
        
        # Step 2: Route to appropriate handler
        if 'MENU' in classification:
            response = handle_menu_query(query)
        elif 'INVENTORY' in classification:
            response = handle_inventory_query(query, user_id)
        elif 'PREDICTION' in classification or 'ORDER' in classification:
            response = handle_prediction_query(query, user_id)
        else:
            response = handle_general_query(query)
    except Exception as e:
        print(f"Chat error: {e}")
        response = "I encountered an error while processing your request. Please check my status."
        classification = "ERROR"
    
    return jsonify({
        'query': query,
        'classification': classification,
        'response': response
    }), 200

def classify_query(query):
    """Classify the user query"""
    prompt = CLASSIFIER_PROMPT.replace("{query}", query)
    response = model.invoke([HumanMessage(content=prompt)])
    return response.content.strip().upper()

def handle_menu_query(query):
    """Handle menu-related queries"""
    response = model.invoke([
        SystemMessage(content="You are helping with restaurant menu management."),
        HumanMessage(content=f"Query: {query}\nProvide helpful guidance on menu processing.")
    ])
    return response.content

def handle_inventory_query(query, user_id):
    """Handle inventory-related queries"""
    response = model.invoke([
        SystemMessage(content="You are an inventory management assistant."),
        HumanMessage(content=f"User query: {query}\nProvide information about stock levels.")
    ])
    return response.content

def handle_prediction_query(query, user_id):
    """Handle prediction-related queries"""
    response = model.invoke([
        SystemMessage(content="You are a demand prediction assistant."),
        HumanMessage(content=f"User query: {query}\nExplain quantity predictions.")
    ])
    return response.content

def handle_general_query(query):
    """Handle general queries"""
    response = model.invoke([
        SystemMessage(content="You are a restaurant management assistant."),
        HumanMessage(content=f"Query: {query}\nProvide general assistance.")
    ])
    return response.content

@chat_bp.route('/orchestrate', methods=['POST'])
def orchestrate_complex_query():
    """Handle complex queries requiring multiple steps"""
    data = request.get_json()
    query = data.get('query', '')
    
    return jsonify({
        'message': 'Complex orchestration endpoint powered by Llama 3 on Groq',
        'query': query,
        'orchestration_plan': [
            'Classify intent via Lama 3',
            'Retrieve context from ChromaDB',
            'Generate response',
            'Validate inventory constraints'
        ]
    }), 200
