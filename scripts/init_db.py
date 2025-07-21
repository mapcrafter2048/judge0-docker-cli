#!/usr/bin/env python3
"""
Judge0 Database Initialization Script
Database initialization and migration script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy import text

from shared.database import create_tables, engine
from shared.config import settings


def init_database():
    """Initialize the database with tables"""
    print("Initializing Judge0 database...")
    print(f"Database URL: {settings.database_url}")
    
    try:
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"Connected to PostgreSQL: {version}")
        
        # Create tables
        create_tables()
        print("✓ Database tables created successfully")
        
        # Create initial data if needed
        print("✓ Database initialization completed")
        
        # Test table creation
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"✓ Created tables: {', '.join(tables)}")
        
        print("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


def reset_database():
    """Reset the database (drop and recreate tables)"""
    print("Resetting Judge0 database...")
    
    try:
        from shared.database import Base, create_tables
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("✓ Dropped existing tables")
        
        # Recreate tables
        create_tables()
        print("✓ Recreated tables")
        
        print("Database reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_database()
    else:
        init_database()


if __name__ == "__main__":
    main()
