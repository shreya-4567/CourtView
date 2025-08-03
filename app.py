import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://localhost/court_scraper")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Import models so their tables are created
    import models  # noqa: F401
    import routes  # noqa: F401
    import auth  # noqa: F401
    from models import User
    
    db.create_all()
    
    # Create demo users if they don't exist
    try:
        if not User.query.filter_by(username='demo').first():
            demo_user = User(
                username='demo',
                email='demo@example.com',
                full_name='Demo User',
                organization='Demo Organization',
                is_verified=True,
                is_active=True
            )
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            logging.info("Created demo user")
        
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@example.com',
                full_name='System Administrator',
                organization='CourtFetch Pro',
                is_verified=True,
                is_active=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            logging.info("Created admin user")
        
        db.session.commit()
        logging.info("Database initialization completed")
        
    except Exception as e:
        logging.error(f"Error creating demo users: {e}")
        db.session.rollback()
