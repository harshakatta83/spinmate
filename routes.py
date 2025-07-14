from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import csv
from io import StringIO
from utils import to_iso8601

from app import app, db
from models import User, Order, OrderItem, ServiceType, OrderStatusUpdate, Feedback, Coupon, ServiceLocation, Pincode, Complaint
from forms import LoginForm, RegisterForm, OrderForm, ProfileForm, StatusUpdateForm, FeedbackForm, PincodeForm
from utils import generate_order_number, calculate_order_total, send_notification


@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'delivery':
            return redirect(url_for('delivery_dashboard'))
        else:
            return redirect(url_for('customer_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if user.is_active:
                login_user(user)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Your account is deactivated. Please contact support.', 'error')
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please use a different email.', 'error')
            return render_template('register.html', form=form)
        
        # Create new user
        user = User(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            password_hash=generate_password_hash(form.password.data),
            role='customer'
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/customer/dashboard', methods=['GET'])
@login_required
def customer_dashboard():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    return render_template('customer_dashboard.html', orders=orders)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    total_orders = Order.query.count()
    deliveries_today = Order.query.filter(
        Order.status == 'delivered',
        db.func.date(Order.updated_at) == date.today()
    ).count()
    pending_complaints = Complaint.query.filter_by(status='open').count()
    # Revenue for the current week
    from datetime import timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    weekly_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.status == 'delivered',
        db.func.date(Order.updated_at) >= week_start
    ).scalar() or 0

    return render_template(
        'admin_dashboard.html',
        total_orders=total_orders,
        deliveries_today=deliveries_today,
        pending_complaints=pending_complaints,
        weekly_revenue=weekly_revenue
    )

@app.route('/delivery/dashboard')
@login_required
def delivery_dashboard():
    if current_user.role != 'delivery':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    pincode_filter = request.args.get('pincode', '')
    type_filter = request.args.get('type', '')

    assigned_orders_query = Order.query.filter_by(delivery_person_id=current_user.id)
    # For dropdown: get all pincodes from all assigned orders
    all_assigned_orders = assigned_orders_query.all()
    pincodes = sorted({o.delivery_address[-6:] for o in all_assigned_orders if o.delivery_address and o.delivery_address[-6:].isdigit()})

    # Now apply filters for display
    if pincode_filter:
        assigned_orders_query = assigned_orders_query.filter(
            (Order.pickup_address.ilike(f"%{pincode_filter}%")) | 
            (Order.delivery_address.ilike(f"%{pincode_filter}%"))
        )
    if type_filter == 'pickup':
        assigned_orders_query = assigned_orders_query.filter(Order.status == 'out_for_pickup')
    elif type_filter == 'delivery':
        assigned_orders_query = assigned_orders_query.filter(Order.status == 'out_for_delivery')
    else:
        assigned_orders_query = assigned_orders_query.filter(Order.status.in_(['picked', 'washing', 'ready','out_for_delivery', 'out_for_pickup']))

    assigned_orders = assigned_orders_query.order_by(Order.pickup_date).all()
    completed_today = Order.query.filter_by(delivery_person_id=current_user.id, status='delivered')\
                                .filter(Order.updated_at >= date.today()).count()
    return render_template('delivery_dashboard.html', 
                         orders=assigned_orders,
                         completed_today=completed_today,
                         pincodes=pincodes,
                         pincode_filter=pincode_filter,
                         type_filter=type_filter)

from forms import PincodeForm, OrderForm

@app.route('/delivery/analytics')
@login_required
def delivery_analytics():
    if current_user.role not in ['delivery', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    from sqlalchemy import func, extract

    # For delivery executives, limit to their orders
    base_query = Order.query
    if current_user.role == 'delivery':
        base_query = base_query.filter_by(delivery_person_id=current_user.id)

    total_assigned = base_query.count()
    total_delivered = base_query.filter(Order.status == 'delivered').count()
    today = date.today()
    deliveries_today = base_query.filter(
        Order.status == 'delivered',
        func.date(Order.updated_at) == today
    ).count()

    pending = base_query.filter(Order.status.in_(['picked', 'washing', 'ready', 'out_for_delivery'])).count()

    # Average delivery time (from picked to delivered)
    delivered_orders = base_query.filter(Order.status == 'delivered').all()
    avg_delivery_time = 0
    if delivered_orders:
        total_time = 0
        count = 0
        for order in delivered_orders:
            picked_time = OrderStatusUpdate.query.filter_by(order_id=order.id, status='picked').order_by(OrderStatusUpdate.timestamp).first()
            delivered_time = OrderStatusUpdate.query.filter_by(order_id=order.id, status='delivered').order_by(OrderStatusUpdate.timestamp).first()
            if picked_time and delivered_time:
                delta = delivered_time.timestamp - picked_time.timestamp
                total_time += delta.total_seconds()
                count += 1
        if count:
            avg_delivery_time = round(total_time / count / 60, 2)  # in minutes

    # Completion rate
    completion_rate = round((total_delivered / total_assigned) * 100, 2) if total_assigned > 0 else 0

    # Time-based data
    daily_trends = db.session.query(
        func.date(Order.updated_at),
        func.count(Order.id)
    ).filter(
        Order.status == 'delivered'
    )
    if current_user.role == 'delivery':
        daily_trends = daily_trends.filter_by(delivery_person_id=current_user.id)

    daily_trends = daily_trends.group_by(func.date(Order.updated_at)).all()

    # Hourly heatmap
    hourly_trends = db.session.query(
        extract('hour', Order.updated_at),
        func.count(Order.id)
    ).filter(
        Order.status == 'delivered'
    )
    if current_user.role == 'delivery':
        hourly_trends = hourly_trends.filter_by(delivery_person_id=current_user.id)

    hourly_trends = hourly_trends.group_by(extract('hour', Order.updated_at)).all()

    # Geolocation (if coordinates stored)
    delivered_locations = []

    # Rescheduled deliveries
    rescheduled_count = OrderStatusUpdate.query.filter_by(status='rescheduled')
    if current_user.role == 'delivery':
        rescheduled_count = rescheduled_count.join(Order).filter(Order.delivery_person_id == current_user.id)
    rescheduled_count = rescheduled_count.count()

    # First attempt success
    failed = base_query.filter(Order.status == 'failed').count()
    first_attempt_success_rate = round((total_delivered / (total_delivered + failed)) * 100, 2) if (total_delivered + failed) > 0 else 100

    # Feedback & complaints
    feedbacks = Feedback.query.join(Order).filter(Order.delivery_person_id == current_user.id) if current_user.role == 'delivery' else Feedback.query
    recent_feedbacks = feedbacks.order_by(Feedback.created_at.desc()).limit(3).all()

    complaints = Complaint.query.join(Order).filter(Order.delivery_person_id == current_user.id) if current_user.role == 'delivery' else Complaint.query
    complaint_count = complaints.count()

    return render_template('delivery_analytics.html',
        total_assigned=total_assigned,
        total_delivered=total_delivered,
        deliveries_today=deliveries_today,
        pending=pending,
        avg_delivery_time=avg_delivery_time,
        completion_rate=completion_rate,
        daily_trends=daily_trends,
        hourly_trends=hourly_trends,
        delivered_locations=delivered_locations,
        rescheduled_count=rescheduled_count,
        first_attempt_success_rate=first_attempt_success_rate,
        recent_feedbacks=recent_feedbacks,
        complaint_count=complaint_count
    )

@app.route('/api/check_pincode', methods=['POST'])
def api_check_pincode():
    data = request.get_json()
    pincode = data.get('pincode')
    serviceable = False
    if pincode:
        serviceable_pincode = Pincode.query.filter_by(pincode=pincode, is_serviceable=True).first()
        if serviceable_pincode:
            serviceable = True
    return jsonify({'serviceable': serviceable})

@app.route('/order/new', methods=['GET', 'POST'])
@login_required
def new_order():
    if current_user.role != 'customer':
        flash('Only customers can place orders.', 'error')
        return redirect(url_for('index'))
    pincode_form = PincodeForm()
    order_form = OrderForm()
    is_serviceable = None  # Initialize is_serviceable

    if pincode_form.validate_on_submit():
        pincode = pincode_form.pincode.data
        serviceable_pincode = Pincode.query.filter_by(pincode=pincode, is_serviceable=True).first()

        if not serviceable_pincode:
            flash('We shall arrive at your place sooner; try different pincode please or request for another pincode', 'error')
            return render_template('order_form.html', pincode_form=pincode_form, order_form=order_form, is_serviceable=False)
        else:
            is_serviceable = True  # Set is_serviceable to True if pincode is valid

    if is_serviceable and order_form.validate_on_submit():
        order = Order(
            customer_id=current_user.id,
            pickup_address=order_form.pickup_address.data,
            delivery_address=order_form.delivery_address.data,
            pickup_date=order_form.pickup_date.data,
            pickup_time=order_form.pickup_time.data,
            special_instructions=order_form.special_instructions.data,
            eco_wash=order_form.eco_wash.data,
            order_number=generate_order_number()
        )
        db.session.add(order)
        db.session.commit()
        flash('Order placed successfully!', 'success')
        return redirect(url_for('add_order_items', order_id=order.id))

    return render_template('order_form.html', pincode_form=pincode_form, order_form=order_form, is_serviceable=is_serviceable)

@app.route('/order/<int:order_id>/items', methods=['GET', 'POST'])
@login_required
def add_order_items(order_id):
    order = Order.query.get_or_404(order_id)

    # Check if user owns this order or is admin
    if current_user.role == 'customer' and order.customer_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('customer_dashboard'))

    services = ServiceType.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        try:
            service_id = request.form.get('service_id')
            item_name = request.form.get('item_name')
            def safe_float(val, default=0.0):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            def safe_int(val, default=1):
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return default

            quantity = safe_int(request.form.get('quantity', 1), 1)
            weight = safe_float(request.form.get('weight', 0), 0.0)
            fabric_type = request.form.get('fabric_type')
            stain_notes = request.form.get('stain_notes')

            # Guard clause: ensure service_id is valid
            if not service_id:
                flash("❌ Please select a service before submitting.", "danger")
                return redirect(url_for('add_order_items', order_id=order.id))

            service = ServiceType.query.get(service_id)
            if not service:
                flash("❌ Selected service not found.", "danger")
                return redirect(url_for('add_order_items', order_id=order.id))

            # Calculate price safely
            price = None
            if weight > 0 and service.price_per_kg is not None:
                price = float(service.price_per_kg) * weight
            elif quantity > 0 and service.price_per_item is not None:
                price = float(service.price_per_item) * quantity

            if price is None:
                flash(f"⚠️ Price not set for {service.name}.", "warning")
                return redirect(url_for('add_order_items', order_id=order.id))

            order_item = OrderItem(
                order_id=order.id,
                service_id=service.id,
                item_name=item_name,
                quantity=quantity,
                weight=weight,
                price=price,
                fabric_type=fabric_type,
                stain_notes=stain_notes
            )

            db.session.add(order_item)
            db.session.commit()
            print(f"Order Item ID: {order_item.id}, Stain Notes: {order_item.stain_notes}")  # Debug
            flash('✅ Item added successfully!', 'success')
            return redirect(url_for('add_order_items', order_id=order.id))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", 'danger')

    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    return render_template('order_details.html', order=order, services=services, order_items=order_items)
@app.route('/order/<int:order_id>/finalize', methods=['POST'])
@login_required
def finalize_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if current_user.role == 'customer' and order.customer_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('customer_dashboard'))
    
    # Calculate totals
    total_weight = sum(float(item.weight or 0) if item.weight not in [None, ''] else 0 for item in order.order_items)
    total_items = sum(int(item.quantity or 0) if item.quantity not in [None, ''] else 0 for item in order.order_items)
    subtotal = sum(float(item.price) if item.price not in [None, ''] else 0 for item in order.order_items)
    
    # Apply discount if any (implement coupon logic here)
    discount = 0
    total_amount = subtotal - discount
    
    # Update order
    order.total_weight = total_weight
    order.total_items = total_items
    order.subtotal = subtotal
    order.discount = discount
    order.total_amount = total_amount
    
    db.session.commit()
    # Clear the session order id after finalizing
    session.pop('current_order_id', None)    
    flash('Order finalized successfully!', 'success')
    return redirect(url_for('order_tracking', order_id=order.id))

@app.route('/order/<int:order_id>')
@login_required
def order_tracking(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Check access permissions
    if (current_user.role == 'customer' and order.customer_id != current_user.id) or \
       (current_user.role == 'delivery' and order.delivery_person_id != current_user.id):
        if current_user.role != 'admin':
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
        if current_user.role == 'delivery' and order.delivery_person_id != current_user.id:
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
    status_updates = OrderStatusUpdate.query.filter_by(order_id=order.id)\
                                           .order_by(OrderStatusUpdate.timestamp.desc()).all()
    
    return render_template('order_tracking.html', order=order, status_updates=status_updates, get_status_progress=get_status_progress)

@app.route('/order/<int:order_id>/update_status', methods=['POST'])
@login_required
def update_order_status(order_id):
    if current_user.role not in ['admin', 'delivery']:
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    
    if current_user.role == 'delivery' and order.delivery_person_id != current_user.id:
        flash('You can only update orders assigned to you.', 'error')
        return redirect(url_for('delivery_dashboard'))
    
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    # Update order status
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    # Add status update record
    status_update = OrderStatusUpdate(
        order_id=order.id,
        status=new_status,
        notes=notes,
        updated_by=current_user.id
    )
    
    db.session.add(status_update)
    db.session.commit()
    
    # Send notification to customer (implement notification system)
    send_notification(order.customer_id, f"Order {order.order_number} status updated to {new_status}")
    
    flash('Order status updated successfully!', 'success')
    return redirect(url_for('order_tracking', order_id=order.id))

@app.route('/admin/complaints')
@login_required
def admin_complaints():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin_complaints.html', complaints=complaints)

@app.route('/admin/complaint/<int:complaint_id>/resolve', methods=['POST'])
@login_required
def resolve_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    complaint.status = 'resolved'
    db.session.commit()
    flash('Complaint resolved successfully.', 'success')
    return redirect(url_for('admin_complaints'))
@app.route('/admin/assign_delivery', methods=['GET'])
@login_required
def admin_assign_delivery():
    status_filter = request.args.get('status', 'all')  # Get the selected status from the query string
    
    orders = Order.query
    if status_filter != 'all':
        orders = orders.filter(Order.status == status_filter)
    
    orders = orders.all()
    delivery_people = User.query.filter_by(role='delivery').all()
    
    return render_template('admin_assign_delivery.html', orders=orders, delivery_people=delivery_people, status_filter=status_filter)

@app.route('/admin/assign_delivery/<int:order_id>', methods=['POST'])
@login_required
def assign_delivery_person(order_id):
    order = Order.query.get_or_404(order_id)
    delivery_person_id = request.form.get('delivery_person_id')
    status = request.form.get('status')  # Get the selected status
    
    if delivery_person_id:
        order.delivery_person_id = delivery_person_id
        order.status = status  # Update order status with the selected status
        db.session.commit()
        flash('Delivery person assigned successfully.', 'success')
    else:
        flash('Please select a delivery person.', 'warning')
    return redirect(url_for('admin_assign_delivery'))

@app.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '').strip()
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.join(User, Order.customer_id == User.id).filter(
            (Order.order_number.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
        )
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    users = User.query.filter_by(role='delivery').all()
    return render_template('admin_orders.html', orders=orders, status_filter=status_filter, users=users)

@app.route('/admin/services/update-price/<int:service_id>', methods=["POST"])
@login_required
def update_service_price(service_id):
    if current_user.role != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('index'))

    service = ServiceType.query.get_or_404(service_id)
    new_price = request.form.get("price")

    if service.is_weight_based:
        service.price_per_kg = float(new_price)
    else:
        service.price_per_item = float(new_price)

    db.session.commit()
    flash("Service price updated successfully.", "success")
    return redirect(url_for('admin_services'))
# filepath: c:\Users\harsha\Downloads\SpinMate_Replit\routes.py

@app.route('/admin/orders/<int:order_id>/assign_delivery', methods=['POST'])
@login_required
def assign_delivery(order_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin_orders'))
    
    order = Order.query.get_or_404(order_id)
    delivery_person_id = request.form.get('delivery_person_id')
    status = request.form.get('status')  # Get the selected status
    
    if not delivery_person_id:
        flash('No delivery person selected.', 'error')
        return redirect(url_for('admin_orders'))
    
    delivery_person = User.query.get(delivery_person_id)
    if not delivery_person or delivery_person.role != 'delivery':
        flash('Invalid delivery person.', 'error')
        return redirect(url_for('admin_orders'))
    
    order.delivery_person_id = delivery_person.id
    order.status = status  # Update order status with the selected status
    db.session.commit()
    flash('Delivery person assigned successfully!', 'success')
    return redirect(url_for('admin_orders'))
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '')
    search = request.args.get('search', '').strip()
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin_users.html', users=users, role_filter=role_filter)

@app.route('/admin/analytics', methods=['GET'])
@login_required
def admin_analytics():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    from sqlalchemy import extract
    from datetime import datetime

    now = datetime.now()
    monthly_orders = Order.query.filter(
        extract('year', Order.created_at) == now.year,
        extract('month', Order.created_at) == now.month,
        Order.status != 'cancelled'
    ).count()
    delivery_person_id = request.args.get('delivery_person_id', type=int)
    delivery_people = User.query.filter_by(role='delivery').all()

    base_query = Order.query
    if delivery_person_id:
        base_query = base_query.filter_by(delivery_person_id=delivery_person_id)

    # Use all orders except cancelled for analytics
    orders_query = Order.query.filter(Order.status != 'cancelled')

    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(Order.status != 'cancelled').scalar() or 0
    order_count = orders_query.count()
    avg_order_value = db.session.query(db.func.avg(Order.total_amount)).filter(Order.status != 'cancelled').scalar() or 0

    # Growth rate calculation (last two months)
    from sqlalchemy import extract
    from datetime import datetime, timedelta

    now = datetime.now()
    this_month = now.month
    last_month = (now.replace(day=1) - timedelta(days=1)).month
    this_year = now.year
    last_month_year = (now.replace(day=1) - timedelta(days=1)).year

    revenue_this_month = db.session.query(db.func.sum(Order.total_amount)).filter(
        extract('year', Order.created_at) == this_year,
        extract('month', Order.created_at) == this_month,
        Order.status != 'cancelled'
    ).scalar() or 0

    revenue_last_month = db.session.query(db.func.sum(Order.total_amount)).filter(
        extract('year', Order.created_at) == last_month_year,
        extract('month', Order.created_at) == last_month,
        Order.status != 'cancelled'
    ).scalar() or 0

    growth_rate = 0
    if revenue_last_month > 0:
        growth_rate = round(((revenue_this_month - revenue_last_month) / revenue_last_month) * 100, 2)

    # Service popularity
    service_stats = db.session.query(
        ServiceType.name,
        db.func.count(OrderItem.id).label('count'),
        db.func.sum(OrderItem.price).label('revenue')
    ).join(OrderItem).join(Order).group_by(ServiceType.id)

    if delivery_person_id:
        service_stats = service_stats.filter(Order.delivery_person_id == delivery_person_id)

    service_stats = service_stats.all()

    # Revenue trend (last 6 months)
    from sqlalchemy import extract
    from collections import OrderedDict
    import calendar

    now = datetime.now()
    months = [(now.year, now.month - i) if now.month - i > 0 else (now.year - 1, 12 + (now.month - i)) for i in range(5, -1, -1)]
    revenue_trend_labels = [calendar.month_abbr[m[1]] for m in months]
    revenue_trend_data = []
    for y, m in months:
        month_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
            db.func.extract('year', Order.created_at) == y,
            db.func.extract('month', Order.created_at) == m,
            Order.payment_status == 'completed'
        )
        if delivery_person_id:
            month_revenue = month_revenue.filter(Order.delivery_person_id == delivery_person_id)
        revenue_trend_data.append(month_revenue.scalar() or 0)

    # Growth rate
    growth_rate = 0
    if len(revenue_trend_data) >= 2 and revenue_trend_data[-2] > 0:
        growth_rate = round(((revenue_trend_data[-1] - revenue_trend_data[-2]) / revenue_trend_data[-2]) * 100, 2)

    # Peak hours
    hourly_orders = db.session.query(
        extract('hour', Order.created_at),
        db.func.count(Order.id)
    ).filter(Order.payment_status == 'completed')
    if delivery_person_id:
        hourly_orders = hourly_orders.filter(Order.delivery_person_id == delivery_person_id)
    hourly_orders = hourly_orders.group_by(extract('hour', Order.created_at)).all()
    if hourly_orders:
        peak_hour = max(hourly_orders, key=lambda x: x[1])[0]
        peak_hours = f"{int(peak_hour):02d}:00 - {int(peak_hour)+1:02d}:00"
    else:
        peak_hours = ""

    # Top service
    if service_stats:
        top_service = max(service_stats, key=lambda x: x[1])[0]
    else:
        top_service = ""

    # Repeat customers
    repeat_customers = db.session.query(Order.customer_id).group_by(Order.customer_id).having(db.func.count(Order.id) > 1).count()
    total_customers = User.query.filter_by(role='customer').count()
    repeat_customers_percent = round((repeat_customers / total_customers) * 100, 2) if total_customers > 0 else 0

    # Recent orders
    recent_orders = base_query.order_by(Order.created_at.desc()).limit(5).all()

    # Recent activities (last 5 status updates)
    recent_activities = db.session.query(OrderStatusUpdate).order_by(OrderStatusUpdate.timestamp.desc()).limit(5).all()

    return render_template('admin_analytics.html',
                        total_revenue=total_revenue,
                        monthly_orders=monthly_orders,
                        avg_order_value=avg_order_value,
                        service_stats=service_stats,
                        delivery_people=delivery_people,
                        selected_delivery_person=delivery_person_id,
                        revenue_trend_labels=revenue_trend_labels,
                        revenue_trend_data=revenue_trend_data,
                        growth_rate=growth_rate,
                        peak_hours=peak_hours,
                        top_service=top_service,
                        repeat_customers_percent=repeat_customers_percent,
                        recent_orders=recent_orders,
                        recent_activities=recent_activities
                    )

@app.route('/order/<int:order_id>/rate', methods=['POST'])
@login_required
def rate_order(order_id):
    order = Order.query.get_or_404(order_id)
    if current_user.id != order.customer_id:
        flash('Access denied.', 'error')
        return redirect(url_for('order_tracking', order_id=order.id))
    try:
        rating = float(request.form.get('rating'))
    except (TypeError, ValueError):
        flash('Invalid rating value.', 'error')
        return redirect(url_for('order_tracking', order_id=order.id))
    if 0 <= rating <= 5:
        order.rating = rating
        db.session.commit()
        flash('Thank you for rating your order!', 'success')
    else:
        flash('Invalid rating value.', 'error')
    return redirect(url_for('order_tracking', order_id=order.id))

@app.route('/order/<int:order_id>/feedback', methods=['POST'])
@login_required
def submit_feedback(order_id):
    order = Order.query.get_or_404(order_id)
    rating = float(request.form['rating'])
    comment = request.form.get('comment', '')
    feedback = Feedback(order_id=order.id, rating=rating, comment=comment)
    db.session.add(feedback)
    order.rating = rating
    db.session.commit()
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('customer_dashboard'))

@app.route('/order/<int:order_id>/complaint', methods=['POST'])
@login_required
def submit_complaint(order_id):
    order = Order.query.get_or_404(order_id)
    description = request.form['description']
    complaint = Complaint(order_id=order.id, user_id=current_user.id, description=description)
    db.session.add(complaint)
    db.session.commit()
    flash('Complaint submitted.', 'success')
    return redirect(url_for('customer_dashboard'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Service Management Routes
@app.route('/admin/services', methods=['GET', 'POST'])
@login_required
def admin_services():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        for service in ServiceType.query.all():
            price_item = request.form.get(f'price_item_{service.id}')
            price_kg = request.form.get(f'price_kg_{service.id}')

            # Update only if valid price is given
            try:
                if price_item:
                    service.price_per_item = float(price_item)
                if price_kg:
                    service.price_per_kg = float(price_kg)
            except ValueError:
                flash(f"Invalid price for service {service.name}", "danger")

        db.session.commit()
        flash("✅ Service prices updated successfully.", "success")
        return redirect(url_for('admin_services'))

    services = ServiceType.query.all()
    pincodes = Pincode.query.all()
    return render_template('admin_services.html', services=services, pincodes=pincodes)

# app.py

@app.route('/admin/services/toggle/<int:service_id>/<pincode>')
@login_required
def toggle_service_location(service_id, pincode):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    service_location = ServiceLocation.query.filter_by(
        service_id=service_id, 
        pincode=pincode
    ).first()
    
    if service_location:
        service_location.is_enabled = not service_location.is_enabled
    else:
        service_location = ServiceLocation(
            service_id=service_id,
            pincode=pincode,
            is_enabled=True
        )
        db.session.add(service_location)
    
    db.session.commit()
    flash('Service availability updated successfully.', 'success')
    return redirect(url_for('admin_services'))

@app.route('/admin/services/<int:service_id>/toggle')
@login_required
def toggle_service_status(service_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    service = ServiceType.query.get_or_404(service_id)
    service.is_active = not service.is_active
    db.session.commit()
    
    status = "enabled" if service.is_active else "disabled"
    flash(f'Service "{service.name}" has been {status}.', 'success')
    return redirect(url_for('admin_services'))

@app.route('/admin/pincodes', methods=['GET', 'POST'])
@login_required
def admin_pincodes():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        pincode = request.form.get('pincode')
        area_name = request.form.get('area_name')
        city = request.form.get('city')
        state = request.form.get('state')
        delivery_fee = request.form.get('delivery_fee') or 0
        is_serviceable = True if request.form.get('is_serviceable') == 'on' else False

        if pincode and area_name and city and state:
            # Check if pincode already exists
            existing = Pincode.query.filter_by(pincode=pincode).first()
            if existing:
                flash('Pincode already exists.', 'warning')
            else:
                new_pin = Pincode(
                    pincode=pincode,
                    area_name=area_name,
                    city=city,
                    state=state,
                    delivery_fee=float(delivery_fee),
                    is_serviceable=is_serviceable
                )
                db.session.add(new_pin)
                db.session.commit()
                flash('Pincode added successfully!', 'success')
        else:
            flash('Please fill all required fields.', 'danger')

        return redirect(url_for('admin_pincodes'))

    pincodes = Pincode.query.all()
    return render_template('admin_pincodes.html', pincodes=pincodes)

@app.route('/admin/pincodes/add', methods=['POST'])
@login_required
def add_pincode():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()

    new_pin = Pincode(
        pincode=data['pincode'],
        area_name=data['area_name'],
        city=data['city'],
        state=data['state'],
        delivery_fee=float(data['delivery_fee']),
        is_serviceable=data['is_serviceable']
    )
    db.session.add(new_pin)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/pincodes/<pincode>/toggle')
@login_required
def toggle_pincode_serviceability(pincode):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    pincode_obj = Pincode.query.filter_by(pincode=pincode).first_or_404()
    pincode_obj.is_serviceable = not pincode_obj.is_serviceable
    db.session.commit()
    
    status = "enabled" if pincode_obj.is_serviceable else "disabled"
    flash(f'Pincode {pincode} serviceability has been {status}.', 'success')
    return redirect(url_for('admin_pincodes'))

# Order Timeline and Tracking Routes
@app.route('/order/<int:order_id>/timeline')
@login_required
def order_timeline(order_id):
    order = Order.query.get_or_404(order_id)
    
    if current_user.role == 'customer' and order.customer_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('customer_dashboard'))
    
    timeline_data = get_order_timeline(order)
    return render_template('order_timeline.html', order=order, timeline=timeline_data)

@app.route('/api/order/<int:order_id>/location')
@login_required
def api_order_location(order_id):
    order = Order.query.get_or_404(order_id)
    
    if current_user.role == 'customer' and order.customer_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    location_data = {
        'pickup_lat': order.pickup_lat,
        'pickup_lng': order.pickup_lng,
        'delivery_lat': order.delivery_lat,
        'delivery_lng': order.delivery_lng,
        'current_location': order.current_location,
        'status': order.status
    }
    
    return jsonify(location_data)

@app.route('/api/order/<int:order_id>/update-location', methods=['POST'])
@login_required
def api_update_order_location(order_id):
    if current_user.role != 'delivery':
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    
    if order.delivery_person_id != current_user.id:
        return jsonify({'error': 'Not assigned to this order'}), 403
    
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat and lng:
        order.current_location = f"{lat},{lng}"
        
        # Add status update
        status_update = OrderStatusUpdate(
            order_id=order.id,
            status=order.status,
            notes=f"Location updated to {lat}, {lng}",
            location=order.current_location,
            updated_by=current_user.id
        )
        db.session.add(status_update)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Location updated successfully'})
    
    return jsonify({'error': 'Invalid location data'}), 400

def get_order_timeline(order):
    """Generate timeline data based on order type and status"""
    timeline_steps = []
    
    # Base timeline for all orders
    base_steps = [
        {'status': 'pending', 'title': 'Order Placed', 'icon': 'fas fa-check', 'color': 'success'},
        {'status': 'assigned', 'title': 'Executive Assigned', 'icon': 'fas fa-user', 'color': 'warning'},
        {'status': 'picked_up', 'title': 'Picked Up', 'icon': 'fas fa-hand-paper', 'color': 'info'},
    ]
    
    # Service-specific processing steps
    service_categories = [item.service.category for item in order.order_items]
    
    if 'dry_clean' in service_categories:
        base_steps.extend([
            {'status': 'dry_cleaning', 'title': 'Dry Cleaning', 'icon': 'fas fa-wind', 'color': 'primary'},
            {'status': 'pressing', 'title': 'Pressing', 'icon': 'fas fa-iron', 'color': 'secondary'},
        ])
    elif 'express' in service_categories:
        base_steps.extend([
            {'status': 'express_washing', 'title': 'Express Washing', 'icon': 'fas fa-tint', 'color': 'primary'},
            {'status': 'express_drying', 'title': 'Express Drying', 'icon': 'fas fa-wind', 'color': 'info'},
        ])
    else:
        base_steps.extend([
            {'status': 'washing', 'title': 'Washing', 'icon': 'fas fa-tint', 'color': 'primary'},
            {'status': 'drying', 'title': 'Ironing', 'icon': 'fas fa-sun', 'color': 'warning'},
            {'status': 'ironing', 'title': 'Ironing', 'icon': 'fas fa-iron', 'color': 'secondary'},
        ])
    
    # Final steps
    base_steps.extend([
        {'status': 'ready', 'title': 'Ready for Delivery', 'icon': 'fas fa-box', 'color': 'success'},
        {'status': 'out_for_delivery', 'title': 'Out for Delivery', 'icon': 'fas fa-truck', 'color': 'warning'},
        {'status': 'delivered', 'title': 'Delivered', 'icon': 'fas fa-home', 'color': 'success'},
    ])
    
    # Mark completed steps
    status_order = [step['status'] for step in base_steps]
    current_index = status_order.index(order.status) if order.status in status_order else 0
    
    for i, step in enumerate(base_steps):
        step['completed'] = i <= current_index
        step['current'] = i == current_index
        
        # Add timestamp if this step is completed
        if step['completed']:
            status_update = OrderStatusUpdate.query.filter_by(
                order_id=order.id, 
                status=step['status']
            ).first()
            step['timestamp'] = status_update.timestamp if status_update else order.created_at
    
    return base_steps

# Export Users
@app.route('/admin/users/export')
@login_required
def export_users():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin_users'))
    users = User.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Email', 'Phone', 'Role', 'Created At'])
    for u in users:
        cw.writerow([u.id, u.name, u.email, u.phone, u.role, u.created_at])
    output = si.getvalue()
    return (output, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=users.csv'
    })

# Export Orders
@app.route('/admin/orders/export')
@login_required
def export_orders():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin_orders'))
    orders = Order.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Order #', 'Customer', 'Date', 'Status', 'Amount'])
    for o in orders:
        cw.writerow([o.order_number, o.customer.name, o.created_at, o.status, o.total_amount])
    output = si.getvalue()
    return (output, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=orders.csv'
    })

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin_users'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        password = request.form.get('password')
        if not all([name, email, phone, role, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('admin_users'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('admin_users'))
        user = User(
            name=name,
            email=email,
            phone=phone,
            role=role,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        flash('User added successfully!', 'success')
        return redirect(url_for('admin_users'))
    return redirect(url_for('admin_users'))

def get_status_progress(status):
    # Example: return a progress percentage or label based on status
    status_map = {
        'pending': 0,
        'out_for_pickup': 10,
        'picked': 30,
        'washing': 50,
        'ready': 70,
        'out_for_delivery': 90,
        'delivered': 100,
        'cancelled': 0
    }
    return status_map.get(status, 0)

from flask import send_file

@app.route('/order/<int:order_id>/invoice')
@login_required
def download_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    customer = order.customer
    order_items = order.order_items

    # Company details
    company_name = "SpinMate"
    company_logo_path = "static/images/logo.png"  # Update if your logo is elsewhere

    # Coupon and discount
    coupon = None
    if hasattr(order, 'coupon_id') and order.coupon_id:
        coupon = Coupon.query.get(order.coupon_id)
    discount = order.discount or 0

    # Payment status
    payment_status = order.payment_status.capitalize() if order.payment_status else "Pending"

    # Generate PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo
    try:
        p.drawImage(company_logo_path, 40, height - 100, width=80, height=60, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass  # If logo not found, skip

    # Company name
    p.setFont("Helvetica-Bold", 20)
    p.drawString(140, height - 60, company_name)

    # Invoice title and order info
    p.setFont("Helvetica-Bold", 16)
    p.drawString(40, height - 120, "INVOICE")
    p.setFont("Helvetica", 12)
    p.drawString(40, height - 140, f"Order ID: {order.order_number}")
    p.drawString(40, height - 160, f"Customer: {customer.name}")
    p.drawString(40, height - 180, f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")

    # Table headers
    y = height - 210
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "Item")
    p.drawString(200, y, "Service")
    p.drawString(320, y, "Qty")
    p.drawString(370, y, "Price")
    p.drawString(440, y, "Stain Notes")
    y -= 20
    p.setFont("Helvetica", 11)

    # Table rows
    for item in order_items:
        p.drawString(40, y, item.item_name)
        service = ServiceType.query.get(item.service_id)
        p.drawString(200, y, service.name if service else "-")
        p.drawString(320, y, str(item.quantity))
        p.drawString(370, y, f"₹{item.price:.2f}")
        p.drawString(440, y, (item.stain_notes or "-")[:25])
        y -= 18
        if y < 100:
            p.showPage()
            y = height - 60

    # Coupon and discount
    y -= 10
    p.setFont("Helvetica-Bold", 12)
    if coupon:
        p.drawString(40, y, f"Coupon Applied: {coupon.code} ({coupon.discount_type} - {coupon.discount_value})")
        y -= 18
    p.drawString(40, y, f"Discount: ₹{discount:.2f}")
    y -= 18

    # Totals
    p.setFont("Helvetica-Bold", 13)
    p.drawString(40, y, f"Subtotal: ₹{order.subtotal:.2f}")
    y -= 18
    p.drawString(40, y, f"Total Amount: ₹{order.total_amount:.2f}")
    y -= 18
    p.drawString(40, y, f"Payment Status: {payment_status}")

    p.setFont("Helvetica-Oblique", 10)
    p.drawString(40, 40, "Thank you for choosing SpinMate!")

    p.showPage()
    p.save()
    buffer.seek(0)

    filename = f"Invoice_{order.order_number}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')    
