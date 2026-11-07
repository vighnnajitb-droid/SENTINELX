from database.session import SessionLocal
from database.models import User
from passlib.context import CryptContext
import os
import argparse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_admin(username, password):
    db = SessionLocal()
    if not db.query(User).filter(User.username == username).first():
        hashed_pw = pwd_context.hash(password)
        user = User(username=username, hashed_password=hashed_pw)
        db.add(user)
        db.commit()
        print(f"User {username} created successfully.")
    else:
        print(f"User {username} already exists.")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed initial admin user")
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"), help="Admin username")
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", "changeme"), help="Admin password")
    args = parser.parse_args()
    seed_admin(args.username, args.password)
