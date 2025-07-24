from app import app, db  # <-- import app and db from your main app.py

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database tables dropped and recreated successfully!")
