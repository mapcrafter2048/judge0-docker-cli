"""Database configuration and models for Judge0 Docker CLI."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID

from .config import settings
from .models import JobStatus, LanguageEnum

# Create engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class
Base = declarative_base()


class Job(Base):
    """Job model for storing execution requests and results."""
    
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_code = Column(Text, nullable=False)
    language = Column(SQLEnum(LanguageEnum), nullable=False)
    stdin = Column(Text)
    
    # Status and metadata
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    worker_id = Column(Integer)  # Track which worker processed the job
    
    # Results
    stdout = Column(Text)
    stderr = Column(Text)
    exit_code = Column(Integer)
    execution_time = Column(Integer)  # in milliseconds
    memory_usage = Column(Integer)  # in KB
    compile_output = Column(Text)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()