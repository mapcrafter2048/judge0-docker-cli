"""Database initialization script for Judge0 Docker CLI."""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database import engine, Base
from shared.config import settings
from shared.models import Job


async def init_database():
    """Initialize the database with tables."""
    print("Initializing Judge0 database...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        
        # Print database info
        print(f"📊 Database URL: {settings.database_url}")
        
        if "sqlite" in settings.database_url:
            db_file = settings.database_url.replace("sqlite:///", "")
            print(f"📁 SQLite database file: {db_file}")
        
        print("\n🎉 Database initialization completed!")
        print("\nNext steps:")
        print("1. Start the API server: python -m api.main")
        print("2. Run tests: python fast_queue_test.py")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database())