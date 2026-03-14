from flask import Flask, jsonify
from flask_cors import CORS
from config.settings import settings
from database.models import db

def create_app():
    app = Flask(__name__, 
                template_folder='../../templates',
                static_folder='../../static')
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = settings.secret_key
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Register blueprints
    from app.api.routes.menu import menu_bp
    from app.api.routes.inventory import inventory_bp
    from app.api.routes.chat import chat_bp
    
    app.register_blueprint(menu_bp, url_prefix='/api/menu')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Kombee AI Backbone Layer API',
            'version': '2.0',
            'status': 'running'
        })
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy'}), 200
    
    return app
