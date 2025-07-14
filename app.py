import os
import logging
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from email_validator import validate_email, EmailNotValidError
from flask_migrate import Migrate

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///spinmate.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

migrate = Migrate(app, db)
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/dashboard')
def dashboard():
    user_id = request.headers.get('X-Replit-User-Id')
    user_name = request.headers.get('X-Replit-User-Name')
    user_roles = request.headers.get('X-Replit-User-Roles')
    
    return render_template('admin_dashboard.html', user_id=user_id, user_name=user_name, user_roles=user_roles)
from email_validator import validate_email, EmailNotValidError
def validate_user_email(email):
    try:
        # Validate the email
        valid = validate_email(email)
        print(f"Email is valid: {valid.email}")
    except EmailNotValidError as e:
        # Email is not valid, exception message is human-readable
        print(str(e))
# Example usage
validate_user_email("admin@spinmate.com")
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()
    
    # Create default admin user if not exists
    from models import User
    from werkzeug.security import generate_password_hash
    
    admin = User.query.filter_by(email='admin@spinmate.com').first()
    if not admin:
        admin = User(
            name='Admin User',
            email='admin@spinmate.com',
            phone='1234567890',
            role='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        
    # Create default delivery person
    delivery = User.query.filter_by(email='delivery@spinmate.com').first()
    if not delivery:
        delivery = User(
            name='Delivery Person',
            email='delivery@spinmate.com',
            phone='9876543210',
            role='delivery',
            password_hash=generate_password_hash('delivery123')
        )
        db.session.add(delivery)
        
    # Create comprehensive service types
    from models import ServiceType, Pincode
    services = [
        # Standard Clothing Items
        {'name': '👕 T-Shirt (Standard)', 'description': 'Regular washing and folding for t-shirts', 'category': 'clothing', 'price_per_item': 25.0, 'is_weight_based': False, 'processing_time_hours': 24},
        {'name': '👖 Trousers', 'description': 'Professional cleaning for trousers', 'category': 'clothing', 'price_per_item': 40.0, 'is_weight_based': False, 'processing_time_hours': 24},
        {'name': '👖 Jeans', 'description': 'Specialized cleaning for denim', 'category': 'clothing', 'price_per_item': 50.0, 'is_weight_based': False, 'processing_time_hours': 24},
        {'name': '🩳 Shorts', 'description': 'Quick wash for shorts', 'category': 'clothing', 'price_per_item': 30.0, 'is_weight_based': False, 'processing_time_hours': 12},
        {'name': '🧥 Jacket (Hanger Pack)', 'description': 'Premium care for jackets with hanger packing', 'category': 'clothing', 'price_per_item': 80.0, 'is_weight_based': False, 'processing_time_hours': 48},
        
        # Service Types
        {'name': '♨️ Steam Iron', 'description': 'Professional steam ironing service', 'category': 'clothing', 'price_per_item': 20.0, 'is_weight_based': False, 'processing_time_hours': 6},
        {'name': '🧼 Wash & Fold', 'description': 'Basic washing and folding service', 'category': 'clothing', 'price_per_item': 25.0, 'is_weight_based': False, 'processing_time_hours': 24},
        {'name': '🧺 Wash & Steam Iron', 'description': 'Complete wash and iron service', 'category': 'clothing', 'price_per_item': 35.0, 'is_weight_based': False, 'processing_time_hours': 24},
        
        # Premium Services
        {'name': '🚀 Express Laundry', 'description': 'Same-day express laundry service', 'category': 'express', 'price_per_kg': 110.0, 'is_weight_based': True, 'processing_time_hours': 8},
        {'name': '🧴 Dry Clean', 'description': 'Professional dry cleaning service', 'category': 'dry_clean', 'price_per_item': 99.0, 'is_weight_based': False, 'processing_time_hours': 48},
        {'name': '✨ Premium Laundry', 'description': 'Premium quality laundry with special care', 'category': 'premium', 'price_per_kg': 150.0, 'is_weight_based': True, 'processing_time_hours': 48},
        {'name': '🧵 Woollen Laundry', 'description': 'Specialized care for woollen garments', 'category': 'woollen', 'price_per_item': 120.0, 'is_weight_based': False, 'processing_time_hours': 72},
        
        # Additional Services
        {'name': '👞 Shoe Cleaning', 'description': 'Professional shoe cleaning and care', 'category': 'additional', 'price_per_item': 150.0, 'is_weight_based': False, 'processing_time_hours': 24},
        {'name': '🧹 Carpet Cleaning', 'description': 'Deep carpet cleaning service', 'category': 'additional', 'price_per_kg': 200.0, 'is_weight_based': True, 'processing_time_hours': 48},
        {'name': '🧼 Curtain Cleaning', 'description': 'Professional curtain cleaning', 'category': 'additional', 'price_per_item': 180.0, 'is_weight_based': False, 'processing_time_hours': 48},
        {'name': '🧥 Leather Cleaning', 'description': 'Specialized leather cleaning and conditioning', 'category': 'additional', 'price_per_item': 250.0, 'is_weight_based': False, 'processing_time_hours': 72},
        {'name': '🧵 Garment Repairs', 'description': 'Professional tailoring and repair services', 'category': 'additional', 'price_per_item': 100.0, 'is_weight_based': False, 'processing_time_hours': 48},
    ]
    
    for service_data in services:
        service = ServiceType.query.filter_by(name=service_data['name']).first()
        if not service:
            service = ServiceType(**service_data)
            db.session.add(service)
    db.session.commit()
    # Create default pincodes for testing
    default_pincodes = [
        {'pincode': '110001', 'area_name': 'Connaught Place', 'city': 'New Delhi', 'state': 'Delhi'},
        {'pincode': '400001', 'area_name': 'Fort', 'city': 'Mumbai', 'state': 'Maharashtra'},
        {'pincode': '560001', 'area_name': 'Shivaji Nagar', 'city': 'Bangalore', 'state': 'Karnataka'},
        {'pincode': '600001', 'area_name': 'Parrys', 'city': 'Chennai', 'state': 'Tamil Nadu'},
    ]

    for pincode_data in default_pincodes:
        existing_pincode = Pincode.query.filter_by(pincode=pincode_data['pincode']).first()
        if not existing_pincode:
            pincode = Pincode(**pincode_data)
            db.session.add(pincode)
    
    db.session.commit()
    logging.info("Database tables created and default users added")
import routes
