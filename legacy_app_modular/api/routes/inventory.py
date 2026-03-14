from flask import Blueprint, request, jsonify
from app.services.inventory_service import InventoryService
from app.services.prediction_service import PredictionService
from database.models import db, Product

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/stock', methods=['GET'])
def get_stock_status():
    """Get current stock status"""
    product_ids = request.args.getlist('product_ids', type=int)
    
    if not product_ids:
        product_ids = None
    
    stock_status = InventoryService.check_stock_status(product_ids)
    
    return jsonify({
        'stock_status': stock_status,
        'total_checked': len(stock_status),
        'low_stock_count': sum(1 for item in stock_status if item['needs_reorder'])
    }), 200

@inventory_bp.route('/low-stock', methods=['GET'])
def get_low_stock():
    """Get products with low stock"""
    threshold = request.args.get('threshold', type=float)
    
    products = InventoryService.get_low_stock_products(threshold)
    
    return jsonify({
        'low_stock_items': [
            {
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'current_stock': p.current_stock,
                'reorder_level': p.reorder_level,
                'unit': p.unit
            }
            for p in products
        ],
        'count': len(products)
    }), 200

@inventory_bp.route('/cart/generate', methods=['POST'])
def generate_cart():
    """Generate order cart based on predictions"""
    data = request.get_json()
    ingredients = data.get('ingredients', [])
    user_id = data.get('user_id', 1)
    
    if not ingredients:
        return jsonify({'error': 'No ingredients provided'}), 400
    
    # Get predictions for these ingredients
    predictions = PredictionService.predict_ingredients_needed(
        ingredients=ingredients,
        menu_items=[],  # Already processed
        user_id=user_id
    )
    
    # Filter only items that need ordering
    order_cart = [p for p in predictions if p['should_order']]
    
    return jsonify({
        'cart': order_cart,
        'total_items': len(order_cart),
        'total_cost': sum(
            item['recommended_order'] * 10  # Placeholder price calculation
            for item in order_cart
        )
    }), 200

@inventory_bp.route('/product/<int:product_id>', methods=['PUT'])
def update_stock(product_id):
    """Update stock for a product"""
    data = request.get_json()
    new_stock = data.get('current_stock')
    
    if new_stock is None:
        return jsonify({'error': 'New stock value required'}), 400
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    product.current_stock = new_stock
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Stock updated for {product.name}',
        'current_stock': product.current_stock
    }), 200
