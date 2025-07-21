from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from shared.models import JobStatus, LanguageEnum
from shared.config import settings

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_code = Column(Text, nullable=False)
    language = Column(SQLEnum(LanguageEnum), nullable=False)
    stdin = Column(Text, nullable=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    
    # Results
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_kb = Column(Integer, nullable=True)
    compile_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self):
        return {
            "job_id": self.id,
            "status": self.status,
            "language": self.language,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": {
                "stdout": self.stdout,
                "stderr": self.stderr,
                "exit_code": self.exit_code,
                "execution_time_ms": self.execution_time_ms,
                "memory_usage_kb": self.memory_usage_kb,
                "compile_output": self.compile_output
            } if self.status == JobStatus.COMPLETED else None,
            "error_message": self.error_message
        }


# Database engine and session
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
