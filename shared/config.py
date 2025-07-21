import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://judge0:judge0_password@localhost:5432/judge0"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    workers_count: int = 4
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    
    # Execution limits
    max_memory_mb: int = 128
    max_cpu_time_ms: int = 5000
    max_wall_time_ms: int = 10000
    enable_network: bool = False
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
