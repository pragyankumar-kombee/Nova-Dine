from database.models import db, Product, Order, OrderDetail
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np
from collections import defaultdict
import pandas as pd

class PredictionService:
    
    @staticmethod
    def predict_quantity(
        product_id: int,
        days_ahead: int = 7,
        user_id: int = None
    ) -> Dict[str, Any]:
        """Predict quantity needed for a product based on historical data"""
        
        # Get historical orders for this product
        query = db.session.query(
            Order.order_date,
            OrderDetail.quantity
        ).join(
            OrderDetail, Order.id == OrderDetail.order_id
        ).filter(
            OrderDetail.product_id == product_id
        )
        
        if user_id:
            query = query.filter(Order.user_id == user_id)
        
        # Get last 90 days of data
        cutoff_date = datetime.now() - timedelta(days=90)
        query = query.filter(Order.order_date >= cutoff_date)
        
        results = query.all()
        
        if not results:
            return {
                'product_id': product_id,
                'predicted_quantity': 0,
                'confidence': 'low',
                'based_on': 'no historical data'
            }
        
        # Simple moving average prediction
        quantities = [r.quantity for r in results]
        avg_quantity = np.mean(quantities)
        std_quantity = np.std(quantities)
        
        # Factor in seasonality (day of week)
        df = pd.DataFrame([(r.order_date, r.quantity) for r in results], 
                         columns=['date', 'quantity'])
        df['day_of_week'] = pd.to_datetime(df['date']).dt.dayofweek
        
        # Get average by day of week
        dow_avg = df.groupby('day_of_week')['quantity'].mean().to_dict()
        
        # Predict for next days_ahead
        predictions = []
        for i in range(days_ahead):
            future_date = datetime.now() + timedelta(days=i)
            dow = future_date.weekday()
            
            if dow in dow_avg:
                predicted = dow_avg[dow]
            else:
                predicted = avg_quantity
            
            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'predicted_quantity': round(predicted, 2)
            })
        
        return {
            'product_id': product_id,
            'predictions': predictions,
            'average_daily': round(avg_quantity, 2),
            'std_deviation': round(std_quantity, 2),
            'confidence': 'high' if len(results) > 30 else 'medium',
            'data_points': len(results)
        }
    
    @staticmethod
    def predict_ingredients_needed(
        ingredients: List[str],
        menu_items: List[Dict],
        user_id: int = None
    ) -> List[Dict]:
        """Predict required quantities for multiple ingredients"""
        
        predictions = []
        
        for ingredient_info in ingredients:
            # Find matching product
            product = Product.query.filter(
                Product.name.ilike(f'%{ingredient_info}%')
            ).first()
            
            if product:
                prediction = PredictionService.predict_quantity(
                    product_id=product.id,
                    user_id=user_id
                )
                
                # Calculate recommended order
                current_stock = product.current_stock
                avg_daily = prediction.get('average_daily', 0)
                
                # Predict for next 7 days
                predicted_need = avg_daily * 7
                
                recommended = max(0, predicted_need - current_stock)
                
                predictions.append({
                    'ingredient': ingredient_info,
                    'product_name': product.name,
                    'current_stock': current_stock,
                    'unit': product.unit,
                    'predicted_need_7days': round(predicted_need, 2),
                    'recommended_order': round(recommended, 2),
                    'should_order': recommended > 0
                })
            else:
                predictions.append({
                    'ingredient': ingredient_info,
                    'product_name': 'Not in inventory',
                    'current_stock': 0,
                    'unit': 'unknown',
                    'predicted_need_7days': 0,
                    'recommended_order': 0,
                    'should_order': False
                })
        
        return predictions