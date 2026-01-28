import logging
from flask import Flask
from flask_cors import CORS
from config.settings import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    logger.info("Starting AtomHumanizer application...")
    
    # Initialize extensions
    CORS(app)
    
    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "version": "2.0.0"}
        
    return app
