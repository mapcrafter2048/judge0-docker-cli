#!/usr/bin/env python3
"""
Simple PostgreSQL Database Viewer for Judge0 Docker CLI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal, Job
from shared.config import settings
from shared.models import JobStatus, LanguageEnum

def view_database_simple():
    """View database contents using SQLAlchemy ORM only"""
    print("🗄️  Judge0 PostgreSQL Database Viewer")
    print("=" * 60)
    
    try:
        # Create session
        db = SessionLocal()
        print(f"📊 Database URL: {settings.database_url}")
        
        # Get job statistics using ORM
        total_jobs = db.query(Job).count()
        completed_jobs = db.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
        failed_jobs = db.query(Job).filter(Job.status == JobStatus.FAILED).count()
        pending_jobs = db.query(Job).filter(Job.status == JobStatus.PENDING).count()
        processing_jobs = db.query(Job).filter(Job.status == JobStatus.PROCESSING).count()
        
        print(f"\n📈 Job Statistics:")
        print(f"   Total Jobs: {total_jobs}")
        print(f"   Completed: {completed_jobs}")
        print(f"   Failed: {failed_jobs}")
        print(f"   Processing: {processing_jobs}")
        print(f"   Pending: {pending_jobs}")
        
        if total_jobs == 0:
            print("\n📭 No jobs found in database")
            return True
        
        # Show language statistics using ORM
        print(f"\n🔤 Language Distribution:")
        for language in LanguageEnum:
            lang_jobs = db.query(Job).filter(Job.language == language).count()
            lang_completed = db.query(Job).filter(Job.language == language, Job.status == JobStatus.COMPLETED).count()
            if lang_jobs > 0:
                success_rate = (lang_completed / lang_jobs * 100) if lang_jobs > 0 else 0
                print(f"   {language.value.upper():12}: {lang_jobs:3} jobs ({lang_completed:3} completed, {success_rate:5.1f}% success)")
        
        # Show recent jobs
        print(f"\n📋 Recent Jobs (Last 10):")
        print("-" * 120)
        print(f"{'ID':<10} {'Language':<12} {'Status':<12} {'Worker':<8} {'Time(ms)':<10} {'Output Preview':<30}")
        print("-" * 120)
        
        recent_jobs = db.query(Job).order_by(Job.created_at.desc()).limit(10).all()
        
        for job in recent_jobs:
            # Format output preview
            output_preview = ""
            if job.stdout:
                output_preview = job.stdout.replace('\n', ' ').strip()[:28]
                if len(job.stdout) > 28:
                    output_preview += "..."
            elif job.stderr:
                stderr_clean = job.stderr.replace('\n', ' ').strip()[:20]
                output_preview = f"ERROR: {stderr_clean}"
            
            # Status icon
            status_icons = {
                JobStatus.COMPLETED: '✅',
                JobStatus.FAILED: '❌',
                JobStatus.PENDING: '🔄',
                JobStatus.PROCESSING: '⚡'
            }
            status_display = f"{status_icons.get(job.status, '❓')} {job.status.value}"
            
            exec_time = f"{job.execution_time}" if job.execution_time else "N/A"
            
            print(f"{job.id[:8]:<10} {job.language.value:<12} {status_display:<12} {str(job.worker_id) if job.worker_id else 'N/A':<8} {exec_time:<10} {output_preview:<30}")
        
        # Show execution time statistics for completed jobs
        completed_jobs_with_time = db.query(Job).filter(
            Job.status == JobStatus.COMPLETED, 
            Job.execution_time.isnot(None)
        ).all()
        
        if completed_jobs_with_time:
            exec_times = [job.execution_time for job in completed_jobs_with_time]
            avg_time = sum(exec_times) / len(exec_times)
            min_time = min(exec_times)
            max_time = max(exec_times)
            
            print(f"\n⏱️  Execution Time Statistics:")
            print(f"   Completed Jobs with Time Data: {len(exec_times)}")
            print(f"   Average Time: {avg_time:.0f}ms ({avg_time/1000:.2f}s)")
            print(f"   Min Time: {min_time:.0f}ms ({min_time/1000:.2f}s)")
            print(f"   Max Time: {max_time:.0f}ms ({max_time/1000:.2f}s)")
        else:
            print(f"\n⏱️  Execution Time Statistics:")
            print("   No execution time data available")
        
        # Show worker performance using ORM
        print(f"\n👥 Worker Performance:")
        
        # Get unique worker IDs
        worker_jobs = db.query(Job).filter(Job.worker_id.isnot(None)).all()
        worker_stats = {}
        
        for job in worker_jobs:
            worker_id = job.worker_id
            if worker_id not in worker_stats:
                worker_stats[worker_id] = {
                    'total': 0,
                    'completed': 0,
                    'exec_times': []
                }
            worker_stats[worker_id]['total'] += 1
            if job.status == JobStatus.COMPLETED:
                worker_stats[worker_id]['completed'] += 1
            if job.execution_time:
                worker_stats[worker_id]['exec_times'].append(job.execution_time)
        
        if worker_stats:
            print(f"   {'Worker':<8} {'Jobs':<6} {'Completed':<10} {'Success%':<8} {'Avg Time':<10}")
            print("   " + "-" * 50)
            for worker_id in sorted(worker_stats.keys()):
                stats = worker_stats[worker_id]
                success_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                avg_time = sum(stats['exec_times']) / len(stats['exec_times']) if stats['exec_times'] else 0
                avg_time_display = f"{avg_time:.0f}ms" if avg_time > 0 else "N/A"
                print(f"   {worker_id:<8} {stats['total']:<6} {stats['completed']:<10} {success_rate:<7.1f}% {avg_time_display:<10}")
        else:
            print("   No worker data available")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def view_job_details(job_id):
    """View detailed information for a specific job"""
    try:
        db = SessionLocal()
        job = db.query(Job).filter(Job.id.like(f"{job_id}%")).first()
        
        if not job:
            print(f"❌ Job with ID starting with '{job_id}' not found")
            return False
        
        print(f"\n🔍 Job Details: {job.id}")
        print("=" * 60)
        print(f"Language: {job.language.value}")
        print(f"Status: {job.status.value}")
        print(f"Worker ID: {job.worker_id or 'N/A'}")
        print(f"Created: {job.created_at}")
        print(f"Started: {job.started_at or 'N/A'}")
        print(f"Completed: {job.completed_at or 'N/A'}")
        print(f"Execution Time: {job.execution_time}ms" if job.execution_time else "Execution Time: N/A")
        print(f"Exit Code: {job.exit_code}" if job.exit_code is not None else "Exit Code: N/A")
        
        print("\n📝 Source Code:")
        print("-" * 40)
        print(job.source_code)
        
        if job.stdin:
            print("\n📥 Standard Input:")
            print("-" * 40)
            print(job.stdin)
        
        if job.stdout:
            print("\n📤 Standard Output:")
            print("-" * 40)
            print(job.stdout)
        
        if job.stderr:
            print("\n❌ Standard Error:")
            print("-" * 40)
            print(job.stderr)
        
        if job.compile_output:
            print("\n🔧 Compile Output:")
            print("-" * 40)
            print(job.compile_output)
        
        if job.error_message:
            print("\n💥 Error Message:")
            print("-" * 40)
            print(job.error_message)
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error viewing job details: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # View specific job details
        job_id = sys.argv[1]
        view_job_details(job_id)
    else:
        # View database overview
        view_database_simple()

if __name__ == "__main__":
    main()
