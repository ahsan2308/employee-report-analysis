"""Shared FastAPI dependencies."""
from app.database import get_database


def get_db():
    """Yield a database session for one request and close it afterwards."""
    db_instance = get_database()
    session = db_instance.create_session()
    try:
        yield session
    finally:
        session.close()
