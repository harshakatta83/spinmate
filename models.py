from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False,
                     default='customer')  # customer, admin, delivery
    address = db.Column(db.Text)
    wallet_balance = db.Column(db.Float, default=0.0)
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    orders = db.relationship('Order', lazy=True, foreign_keys='Order.customer_id', overlaps="customer")
    delivery_orders = db.relationship('Order', lazy=True, foreign_keys='Order.delivery_person_id', overlaps="delivery_person,assigned_orders")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ServiceLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service_type.id'), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('service_id', 'pincode', name='unique_service_pincode'), )


class ServiceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)  # clothing, express, dry_clean, premium, woollen, additional
    price_per_kg = db.Column(db.Float)
    price_per_item = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    is_weight_based = db.Column(db.Boolean, default=False)  # True for kg-based pricing
    processing_time_hours = db.Column(db.Integer, default=24)  # Processing time in hours

    # Relationships
    order_items = db.relationship('OrderItem', backref='service', lazy=True)
    service_locations = db.relationship('ServiceLocation', backref='service', lazy=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pickup_address = db.Column(db.Text, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    pickup_date = db.Column(db.Date, nullable=False)
    pickup_time = db.Column(db.Time, nullable=False)
    special_instructions = db.Column(db.Text)  # For customer notes
    eco_wash = db.Column(db.Boolean, default=False)
    total_weight = db.Column(db.Float, default=0.0)
    total_items = db.Column(db.Integer, default=0)
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='pending')
    status = db.Column(db.String(20), default='pending')  # pending, picked, washing, ready, delivered, cancelled, out_for_delivery, out_for_pickup
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    rating = db.Column(db.Float, nullable=True)  # For 5-star decimal ratings

    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id], overlaps="orders")
    delivery_person = db.relationship('User', backref='assigned_orders', foreign_keys=[delivery_person_id], overlaps="delivery_orders")
    order_items = db.relationship('OrderItem', backref='order', lazy=True)
    complaints = db.relationship('Complaint', backref='order', lazy=True)
    feedback = db.relationship('Feedback', backref='order_ref', lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service_type.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, nullable=False)
    fabric_type = db.Column(db.String(50))
    stain_notes = db.Column(db.Text)  # For stain notes
    item_status = db.Column(db.String(20), default='pending')  # pending, processing, washing, dry_cleaning, ironing, ready


class OrderStatusUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    location = db.Column(db.String(200))  # For tracking updates
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updater = db.relationship('User', backref='status_updates')


class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    discount_type = db.Column(db.String(20), nullable=False)  # percentage, fixed
    discount_value = db.Column(db.Float, nullable=False)
    min_order_amount = db.Column(db.Float, default=0.0)
    max_discount = db.Column(db.Float)
    usage_limit = db.Column(db.Integer)
    used_count = db.Column(db.Integer, default=0)
    valid_from = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)  # Allow decimal ratings
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('User', backref='feedback_given')


class Pincode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pincode = db.Column(db.String(10), unique=True, nullable=False)
    area_name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    is_serviceable = db.Column(db.Boolean, default=True)
    delivery_fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('User', backref='complaints')