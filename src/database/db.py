"""
Database connection and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from .models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./demo.db")


class Database:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or DATABASE_URL
        # Handle SQLite async compatibility
        if self.db_url.startswith("sqlite"):
            self.engine = create_engine(
                self.db_url, 
                connect_args={"check_same_thread": False},
                echo=False
            )
        else:
            self.engine = create_engine(self.db_url, echo=False)
        
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables"""
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_instance(self) -> Session:
        """Get a session instance (caller must manage lifecycle)"""
        return self.SessionLocal()


# Global database instance
_db_instance = None


def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.create_tables()
    return _db_instance
