from app import app, db
from models import User

with app.app_context():
    # Reset tables
    db.drop_all()
    db.create_all()

    # Create default admin user
    admin = User(
        name='Admin',
        email='admin@spinmate.com',
        phone='9999999999',
        password_hash='adminpass',  # Use proper hash in real case
        role='admin',
        is_active=True
    )
    db.session.add(admin)
    db.session.commit()
    print("✅ Database reset complete with default admin.")
