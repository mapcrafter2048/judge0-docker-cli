from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import uuid

from shared.models import (
    SubmissionRequest, 
    SubmissionResponse, 
    JobResponse, 
    JobStatus,
    ExecutionResult
)
from shared.database import get_db, Job, Base, engine
from shared.background_executor import background_executor
from shared.utils import get_logger
from shared.config import settings

# Setup logging
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info("Judge0 API started successfully")
    yield
    # Shutdown
    logger.info("Judge0 API shutting down")


# Create FastAPI app
app = FastAPI(
    title="Judge0 API",
    description="Containerized Online Judge System with Docker CLI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Judge0 API",
        "status": "healthy",
        "version": "1.0.0",
        "description": "Superior Docker CLI Multi-Worker Online Judge"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test database connection
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    try:
        # Test background executor
        active_jobs = background_executor.get_active_jobs_count()
        executor_status = f"healthy (active jobs: {active_jobs})"
    except Exception as e:
        executor_status = f"unhealthy: {str(e)}"
    
    overall_healthy = (db_status == "healthy" and
                       "healthy" in executor_status)
    
    return {
        "service": "Judge0 API",
        "database": db_status,
        "background_executor": executor_status,
        "overall_status": "healthy" if overall_healthy else "unhealthy",
        "max_workers": settings.max_workers
    }


@app.post("/submissions", response_model=SubmissionResponse)
async def submit_code(
    submission: SubmissionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submit code for execution"""
    try:
        # Create job record in database
        job = Job(
            id=str(uuid.uuid4()),
            source_code=submission.source_code,
            language=submission.language,
            stdin=submission.stdin,
            status=JobStatus.PENDING
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Schedule job for background execution
        background_tasks.add_task(
            background_executor.execute_code_job,
            job.id,
            submission.source_code,
            submission.language.value,
            submission.stdin
        )
        
        logger.info(f"Job {job.id} submitted for language "
                    f"{submission.language}")
        
        return SubmissionResponse(
            job_id=job.id,
            status=JobStatus.PENDING,
            message="Job submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting job: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to submit job: {str(e)}")


@app.get("/submissions/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get job status and results"""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Build response
        result = None
        if job.status == JobStatus.COMPLETED:
            result = ExecutionResult(
                stdout=job.stdout,
                stderr=job.stderr,
                exit_code=job.exit_code,
                execution_time_ms=job.execution_time,
                memory_usage_kb=job.memory_usage,
                compile_output=job.compile_output
            )
        
        response = JobResponse(
            job_id=job.id,
            status=job.status,
            language=job.language,
            created_at=job.created_at,
            completed_at=job.completed_at,
            result=result,
            error_message=job.error_message
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to get job: {str(e)}")


@app.get("/submissions")
async def list_jobs(
    limit: int = 10,
    offset: int = 0,
    status: JobStatus = None,
    db: Session = Depends(get_db)
):
    """List jobs with pagination and filtering"""
    try:
        query = db.query(Job)
        
        if status:
            query = query.filter(Job.status == status)
        
        jobs = (query.order_by(Job.created_at.desc())
                .offset(offset).limit(limit).all())
        
        # Convert jobs to dict
        job_list = []
        for job in jobs:
            job_dict = {
                "job_id": job.id,
                "status": job.status,
                "language": job.language,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "execution_time": job.execution_time
            }
            job_list.append(job_dict)
        
        return {
            "jobs": job_list,
            "total": query.count(),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to list jobs: {str(e)}")


@app.get("/languages")
async def get_supported_languages():
    """Get list of supported programming languages"""
    from shared.models import LANGUAGE_CONFIG
    
    languages = []
    for lang, config in LANGUAGE_CONFIG.items():
        languages.append({
            "id": lang.value,
            "name": lang.value.title(),
            "file_extension": config["file_extension"],
            "timeout_ms": config["timeout"],
            "memory_limit_mb": config["memory_limit"]
        })
    
    return {"languages": languages}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )