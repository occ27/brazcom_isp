import os
from dotenv import load_dotenv
load_dotenv()
from app.core.database import engine
from sqlalchemy import text

print('Testing DB connection...')
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('DB connection successful:', result.fetchone())
except Exception as e:
    print('DB connection failed:', str(e))