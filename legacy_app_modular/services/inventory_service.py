from database.models import db, Product, Order, OrderDetail
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any

class InventoryService:
    
    @staticmethod
    def check_stock_status(product_ids: List[int] = None):
        """Check current stock levels for products"""
        query = Product.query
        
        if product_ids:
            query = query.filter(Product.id.in_(product_ids))
        
        products = query.all()
        
        stock_status = []
        for product in products:
            status = {
                'product_id': product.id,
                'product_name': product.name,
                'category': product.category,
                'current_stock': product.current_stock,
                'reorder_level': product.reorder_level,
                'unit': product.unit,
                'needs_reorder': product.current_stock <= product.reorder_level
            }
            stock_status.append(status)
        
        return stock_status
    
    @staticmethod
    def get_low_stock_products(threshold: float = None):
        """Get products below reorder level"""
        query = Product.query.filter(Product.current_stock <= Product.reorder_level)
        
        if threshold:
            query = query.filter(Product.current_stock <= threshold)
        
        return query.all()
    
    @staticmethod
    def get_ingredient_stock(ingredients: List[str]) -> Dict[str, Any]:
        """Get stock information for specific ingredients"""
        # Fuzzy matching of ingredient names to products
        stock_info = {}
        
        for ingredient in ingredients:
            # Search for similar product names
            products = Product.query.filter(
                Product.name.ilike(f'%{ingredient}%')
            ).all()
            
            if products:
                for product in products:
                    stock_info[ingredient] = {
                        'product_id': product.id,
                        'product_name': product.name,
                        'current_stock': product.current_stock,
                        'unit': product.unit,
                        'reorder_level': product.reorder_level
                    }
            else:
                stock_info[ingredient] = {
                    'product_id': None,
                    'product_name': 'Not found in inventory',
                    'current_stock': 0,
                    'unit': 'unknown',
                    'reorder_level': 0
                }
        
        return stock_info