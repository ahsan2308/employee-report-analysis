import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import psycopg2
from app.core.config import DATABASE_URL  # Now it should work

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()

    print(f" Successfully connected to PostgreSQL. Version: {db_version[0]}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f" Database connection failed: {e}")
