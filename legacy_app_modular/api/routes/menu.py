from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
import os
from app.services.menu_service import MenuExtractionService
from app.services.inventory_service import InventoryService
from app.services.prediction_service import PredictionService
from database.models import db, MenuDocument, User

menu_bp = Blueprint('menu', __name__)
menu_service = MenuExtractionService()

@menu_bp.route('/upload', methods=['POST'])
def upload_menu():
    """Handle menu upload and processing"""
    try:
        if 'menu' not in request.files:
            return jsonify({'error': 'No menu file provided'}), 400
        
        file = request.files['menu']
        user_id = request.form.get('user_id', 1)  # Default user for demo
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Secure filename and save temporarily
        filename = secure_filename(file.filename)
        
        # Extract text based on file type
        if filename.endswith('.pdf'):
            menu_text = menu_service.extract_text_from_pdf(file)
        else:
            menu_text = file.read().decode('utf-8')
        
        # Extract dishes and ingredients using AI
        extracted_data = menu_service.extract_dishes_and_ingredients(menu_text)
        
        # Store in vector database
        num_stored = menu_service.store_menu_in_vector_db(user_id, extracted_data)
        
        # Save to database
        menu_doc = MenuDocument(
            user_id=user_id,
            filename=filename,
            content=menu_text,
            processed_data=extracted_data
        )
        db.session.add(menu_doc)
        db.session.commit()
        
        # Check stock for ingredients
        all_ingredients = []
        for dish in extracted_data.get('dishes', []):
            all_ingredients.extend(dish.get('ingredients', []))
        
        stock_info = InventoryService.get_ingredient_stock(all_ingredients)
        
        # Get predictions
        predictions = PredictionService.predict_ingredients_needed(
            ingredients=list(stock_info.keys()),
            menu_items=extracted_data.get('dishes', []),
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Menu processed successfully',
            'data': {
                'dishes': extracted_data.get('dishes', []),
                'total_dishes': len(extracted_data.get('dishes', [])),
                'total_ingredients': len(all_ingredients),
                'vector_store_entries': num_stored,
                'inventory_check': stock_info,
                'predictions': predictions
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/process', methods=['POST'])
def process_menu_text():
    """Process menu text directly"""
    try:
        data = request.get_json()
        menu_text = data.get('menu_text', '')
        user_id = data.get('user_id', 1)
        
        if not menu_text:
            return jsonify({'error': 'No menu text provided'}), 400
        
        # Extract dishes and ingredients
        extracted_data = menu_service.extract_dishes_and_ingredients(menu_text)
        
        # Store in vector database
        menu_service.store_menu_in_vector_db(user_id, extracted_data)
        
        return jsonify({
            'success': True,
            'data': extracted_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/history/<int:user_id>', methods=['GET'])
def get_menu_history(user_id):
    """Get menu upload history for a user"""
    menus = MenuDocument.query.filter_by(user_id=user_id).order_by(
        MenuDocument.uploaded_at.desc()
    ).all()
    
    return jsonify({
        'menus': [
            {
                'id': m.id,
                'filename': m.filename,
                'uploaded_at': m.uploaded_at.isoformat(),
                'num_dishes': len(m.processed_data.get('dishes', [])) if m.processed_data else 0
            }
            for m in menus
        ]
    }), 200