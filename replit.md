# SpinMate - Fast. Fresh. Flawless.

## Overview

SpinMate is a comprehensive laundry service management system built with Flask. The application provides a complete solution for managing laundry operations including customer orders, delivery tracking, admin management, and service analytics. The system supports multiple user roles (customers, admin, delivery personnel) with role-based access control.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python 3.11) with SQLAlchemy ORM
- **Database**: SQLite (development) with PostgreSQL support for production
- **Authentication**: Flask-Login with password hashing via Werkzeug
- **Forms**: Flask-WTF with WTForms for form handling and validation
- **PDF Generation**: ReportLab for invoice and report generation
- **Deployment**: Gunicorn WSGI server with autoscale deployment target

### Frontend Architecture
- **Templates**: Jinja2 templating engine
- **Styling**: Bootstrap 5.3.0 with Font Awesome icons
- **JavaScript**: Vanilla JS with modern ES6+ features
- **Responsive Design**: Mobile-first approach with Bootstrap grid system
- **UI Components**: Custom CSS with CSS variables for theming

### Database Schema
The application uses SQLAlchemy with the following core models:
- **User**: Handles customers, admin, and delivery personnel with role-based access
- **ServiceType**: Manages different laundry services (wash & fold, dry clean, etc.)
- **Order**: Core order management with status tracking
- **OrderItem**: Individual items within orders
- Additional models for status updates, feedback, and coupons (referenced but not fully implemented)

## Key Components

### User Management
- Multi-role authentication system (customer, admin, delivery)
- Profile management with wallet balance and loyalty points
- Secure password hashing and session management

### Order Management
- Order creation with pickup/delivery scheduling
- Item-based service selection with pricing calculation
- Status tracking system (pending → picked → washing → ready → delivered)
- Order numbering system with unique identifiers

### Service System
- Configurable service types with per-kg and per-item pricing
- Default services include: Wash & Fold, Wash & Iron, Dry Clean, Steam Press, Delicate Care
- Support for fabric types and special care instructions

### Dashboard System
- **Customer Dashboard**: Order history, wallet balance, loyalty points
- **Admin Dashboard**: Order management, user management, analytics
- **Delivery Dashboard**: Assigned orders and completion tracking

### Form System
- Comprehensive form handling for registration, login, orders
- Validation with proper error handling
- Support for various input types including date/time selection

## Data Flow

1. **User Registration**: New users register with email/phone validation
2. **Order Creation**: Customers create orders with pickup details and scheduling
3. **Order Processing**: Items are added to orders with service type selection
4. **Status Updates**: Orders progress through defined status stages
5. **Delivery Management**: Delivery personnel receive and complete assignments
6. **Analytics**: Admin views aggregate data and performance metrics

## External Dependencies

### Python Packages
- **Flask** (3.1.1): Core web framework
- **Flask-SQLAlchemy** (3.1.1): Database ORM
- **Flask-Login** (0.6.3): User session management  
- **Flask-WTF** (1.2.2): Form handling
- **Gunicorn** (23.0.0): Production WSGI server
- **ReportLab** (4.4.2): PDF generation
- **psycopg2-binary** (2.9.10): PostgreSQL adapter

### Frontend Dependencies
- **Bootstrap** (5.3.0): CSS framework
- **Font Awesome** (6.4.0): Icon library
- **Chart.js**: Analytics visualization (referenced in templates)

### System Dependencies
- **PostgreSQL**: Production database
- **OpenSSL**: Security and encryption
- **FreeType**: Font rendering for PDF generation

## Deployment Strategy

### Development Environment
- SQLite database for local development
- Flask development server with debug mode
- Environment variables for configuration

### Production Environment
- **Deployment Target**: Autoscale deployment on Replit
- **Web Server**: Gunicorn with multiple worker processes
- **Database**: PostgreSQL with connection pooling
- **Session Management**: Secure session keys via environment variables
- **Proxy Configuration**: ProxyFix middleware for proper header handling

### Configuration Management
- Environment-based database URLs
- Configurable session secrets
- SQLAlchemy engine options for production optimization
- Connection pooling with pre-ping health checks

## Recent Features (June 27, 2025)

### Comprehensive Service Management
- Implemented detailed pricing structure as requested:
  - T-Shirt (Standard): ₹25
  - Trousers: ₹40  
  - Jeans: ₹50
  - Shorts: ₹30
  - Jacket (Hanger Pack): ₹80
  - Steam Iron: ₹20
  - Wash & Fold: ₹25
  - Wash & Steam Iron: ₹35
  - Express Laundry: ₹110/kg
  - Dry Clean: ₹99
  - Premium Laundry: ₹150/kg
  - Woollen Laundry: ₹120
  - Additional services: Shoe cleaning (₹150), Carpet cleaning (₹200/kg), Curtain cleaning (₹180), Leather cleaning (₹250), Garment repairs (₹100)

### Location-Based Service Management
- Admin can enable/disable services by pincode
- Service availability matrix with full pincode management
- Geographic coverage tracking for business expansion

### Advanced Order Timeline System
- Service-specific processing workflows:
  - Dry cleaning: pickup → dry cleaning → pressing → delivery
  - Express: pickup → express washing → express drying → delivery  
  - Standard: pickup → washing → drying → ironing → delivery
- Real-time status updates with timestamps
- Processing time estimates based on service type

### Google Maps Integration
- Live order tracking with interactive maps
- Pickup and delivery location markers
- Delivery executive location updates
- Customer tracking interface
- Navigation assistance for delivery personnel

### Enhanced Admin Interface
- Clean sidebar design with olive color scheme (no blue elements)
- Professional service management dashboard
- Pincode serviceability controls
- Real-time analytics and status monitoring

## System Architecture Updates

### New Database Models
- **ServiceLocation**: Links services to specific pincodes with enable/disable functionality
- **Pincode**: Manages serviceable areas with delivery fees
- Enhanced **Order** model with GPS coordinates and location tracking
- Enhanced **ServiceType** with categories, processing times, and weight-based pricing

### API Endpoints
- `/admin/services` - Service management interface
- `/admin/pincodes` - Pincode management interface
- `/order/<id>/timeline` - Interactive order timeline with maps
- `/api/order/<id>/location` - Location data for tracking
- `/api/order/<id>/update-location` - Live location updates from delivery personnel

## Changelog

- June 25, 2025: Initial setup
- June 27, 2025: Complete service management system with pricing, location controls, timeline tracking, and Google Maps integration

## User Preferences

Preferred communication style: Simple, everyday language.
Design preference: Premium light olive color scheme with black text (no blue elements).
Timeline requirements: Service-specific workflows with real-time tracking and Google Maps integration.