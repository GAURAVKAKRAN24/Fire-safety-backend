from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://postgres:12345@localhost:5432/fire_safety_db"

# Render / Heroku compatibility: convert postgres:// to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        print("Database Connection established successfully.")
except Exception as e:
    print(f"Error occurred while connecting to the database: {e}")