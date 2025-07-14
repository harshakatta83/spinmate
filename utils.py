
import uuid
from datetime import datetime
import logging

def generate_order_number():
    """Generate a unique order number"""
    import random
    import string

    try:
        timestamp = datetime.now().strftime('%Y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=4))
        order_number = f"ORD{timestamp}{random_suffix}"

        # Ensure uniqueness
        from models import Order
        while Order.query.filter_by(order_number=order_number).first():
            random_suffix = ''.join(random.choices(string.digits, k=4))
            order_number = f"ORD{timestamp}{random_suffix}"

        return order_number
    except Exception as e:
        # Fallback order number generation
        import time
        return f"ORD{int(time.time())}"

def calculate_order_total(order_items):
    """Calculate total amount for order items"""
    try:
        if not order_items:
            return 0.0

        subtotal = sum(float(item.price or 0) for item in order_items if item.price is not None)
        # Add any taxes, fees, or discounts here
        return round(subtotal, 2)
    except (TypeError, ValueError):
        return 0.0

def send_notification(user_id, message):
    """Send notification to user (placeholder for actual implementation)"""
    # This would integrate with email service, SMS, or push notifications
    logging.info(f"Notification to user {user_id}: {message}")
    # For now, just log the notification
    pass

def get_status_color(status):
    """Get color class for order status"""
    status_colors = {
        'pending': 'warning',
        'picked': 'info',
        'washing': 'primary',
        'ready': 'success',
        'delivered': 'success',
        'cancelled': 'danger'
    }
    return status_colors.get(status, 'secondary')

def format_currency(amount):
    """Format amount as currency"""
    try:
        return f"₹{float(amount):.2f}" if amount is not None else "₹0.00"
    except (TypeError, ValueError):
        return "₹0.00"

def get_delivery_time_slots():
    """Get available delivery time slots"""
    return [
        ('09:00-12:00', '9:00 AM - 12:00 PM'),
        ('12:00-15:00', '12:00 PM - 3:00 PM'),
        ('15:00-18:00', '3:00 PM - 6:00 PM'),
        ('18:00-21:00', '6:00 PM - 9:00 PM')
    ]

def validate_phone_number(phone):
    """Validate phone number format"""
    import re
    pattern = r'^[6-9]\d{9}$'
    return re.match(pattern, phone) is not None

def calculate_loyalty_points(order_amount):
    """Calculate loyalty points based on order amount"""
    try:
        # 1 point per ₹10 spent
        return int(float(order_amount or 0) // 10)
    except (TypeError, ValueError):
        return 0

def apply_coupon(order_total, coupon_code):
    """Apply coupon discount to order total"""
    from models import Coupon
    from datetime import date
    
    try:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        if not coupon:
            return order_total, 0, "Invalid coupon code"
        
        if coupon.valid_until < date.today():
            return order_total, 0, "Coupon has expired"
        
        if order_total < coupon.min_order_amount:
            return order_total, 0, f"Minimum order amount ₹{coupon.min_order_amount} required"
        
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return order_total, 0, "Coupon usage limit exceeded"
        
        if coupon.discount_type == 'percentage':
            discount = (order_total * coupon.discount_value) / 100
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = coupon.discount_value
        
        final_total = max(0, order_total - discount)
        return final_total, discount, "Coupon applied successfully"
    except Exception as e:
        logging.error(f"Error applying coupon: {e}")
        return order_total, 0, "Error applying coupon"

def to_iso8601(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, str):
        try:
            print("Trying to parse:", val, "Type:", type(val))  # << Add this line
            parsed = datetime.fromisoformat(val)
            return parsed.isoformat()
        except Exception as e:
            print("Failed to parse:", val, "Exception:", e)
            return val
    return str(val)