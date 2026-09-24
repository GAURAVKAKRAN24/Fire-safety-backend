from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:12345@localhost:5432/fire_safety_db"

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        print("Database Connection established successfully.")
except Exception as e:
    print(f"Error occurred while connecting to the database: {e}")