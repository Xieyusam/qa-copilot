import os
import sys

# Ensure the app module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_admin(username: str = "admin", password: str = "admin123"):
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.username == username).first()
        if existing_admin:
            print(f"Admin user '{username}' already exists.")
            return

        new_admin = User(
            username=username,
            hashed_password=get_password_hash(password),
            role="admin",
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        print(f"Successfully created admin user: {username} with password: {password}")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create an admin user for QA Copilot")
    parser.add_argument("--username", "-u", default="admin", help="Username for the admin account")
    parser.add_argument("--password", "-p", default="admin123", help="Password for the admin account")
    args = parser.parse_args()
    
    create_admin(args.username, args.password)
