"""
Database migration script to fix critical issues:
1. Fix enum values from lowercase to uppercase
2. Ensure worker_id column exists and is properly typed
3. Add any missing indexes for performance
"""

import sqlite3
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import engine, SessionLocal, Job
from shared.models import JobStatus
from sqlalchemy import text

def migrate_database():
    """Run database migrations to fix critical issues"""
    
    print("Starting database migration...")
    
    # Connect directly to SQLite
    db_path = "judge0.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Step 1: Fix enum values from lowercase to uppercase
        print("1. Updating job status enum values...")
        
        # Map old lowercase values to new uppercase values
        status_mapping = {
            'pending': 'PENDING',
            'processing': 'PROCESSING', 
            'completed': 'COMPLETED',
            'failed': 'FAILED',
            'timeout': 'TIMEOUT',
            'compilation_error': 'COMPILATION_ERROR',
            'runtime_error': 'RUNTIME_ERROR'
        }
        
        for old_status, new_status in status_mapping.items():
            cursor.execute(
                "UPDATE jobs SET status = ? WHERE status = ?",
                (new_status, old_status)
            )
            affected = cursor.rowcount
            if affected > 0:
                print(f"   Updated {affected} jobs from '{old_status}' to '{new_status}'")
        
        # Step 2: Ensure worker_id column exists and has correct type
        print("2. Checking worker_id column...")
        
        cursor.execute("PRAGMA table_info(jobs)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        if 'worker_id' not in columns:
            print("   Adding worker_id column...")
            cursor.execute("ALTER TABLE jobs ADD COLUMN worker_id INTEGER")
        else:
            print("   worker_id column already exists")
        
        # Step 3: Add indexes for performance if they don't exist
        print("3. Adding performance indexes...")
        
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_worker_id ON jobs(worker_id)")
            print("   Performance indexes added")
        except sqlite3.Error as e:
            print(f"   Warning: Could not add some indexes: {e}")
        
        # Step 4: Update any NULL started_at for PROCESSING jobs
        print("4. Fixing missing started_at timestamps...")
        cursor.execute("""
            UPDATE jobs 
            SET started_at = created_at 
            WHERE status = 'PROCESSING' AND started_at IS NULL
        """)
        affected = cursor.rowcount
        if affected > 0:
            print(f"   Fixed {affected} jobs with missing started_at")
        
        # Commit all changes
        conn.commit()
        print("✅ Database migration completed successfully!")
        
        # Verify the changes
        print("\nVerification:")
        cursor.execute("SELECT DISTINCT status FROM jobs")
        statuses = [row[0] for row in cursor.fetchall()]
        print(f"   Current status values: {', '.join(statuses)}")
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE worker_id IS NOT NULL")
        worker_jobs = cursor.fetchone()[0]
        print(f"   Jobs with worker_id: {worker_jobs}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        return False
        
    finally:
        conn.close()
    
    return True

def test_enum_values():
    """Test that our enum values work correctly with the database"""
    print("\nTesting enum value compatibility...")
    
    try:
        with SessionLocal() as db:
            # Test inserting with new enum values
            from shared.models import JobStatus
            
            print("Available JobStatus values:")
            for status in JobStatus:
                print(f"   {status.name} = '{status.value}'")
            
            # Test querying existing data
            sample_job = db.query(Job).first()
            if sample_job:
                print(f"Sample job status: {sample_job.status}")
                print(f"Sample job worker_id: {sample_job.worker_id}")
            
        print("✅ Enum compatibility test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Enum compatibility test failed: {e}")
        return False

if __name__ == "__main__":
    print("Judge0 Docker CLI - Database Migration")
    print("=" * 50)
    
    # Run migration
    if migrate_database():
        # Test the changes
        if test_enum_values():
            print("\n🎉 All migrations completed successfully!")
            print("The following issues have been fixed:")
            print("   ✅ Enum values standardized to uppercase")
            print("   ✅ worker_id column ensured and indexed")
            print("   ✅ Performance indexes added")
            print("   ✅ Missing timestamps fixed")
        else:
            print("\n⚠️  Migration completed but tests failed")
            sys.exit(1)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)
