"""Configuration management for Judge0 Docker CLI."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database settings
    database_url: str = Field(
        default="sqlite:///./judge0.db",
        description="Database connection URL"
    )
    
    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8080, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    redis_url: str = Field(default='redis://localhost:6379/0', description='Redis connection URL')
    
    # Worker settings
    max_workers: int = Field(default=4, description="Maximum number of workers")
    workers_count: int = Field(default=4, description="Number of worker processes")
    worker_timeout: int = Field(default=300, description="Worker timeout in seconds")
    
    # Docker settings
    docker_host: str = Field(default="unix:///var/run/docker.sock", description="Docker host connection")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # Container limits
    max_memory_mb: int = Field(default=512, description="Maximum memory per container in MB")
    max_cpu_time_ms: int = Field(default=5000, description="Maximum CPU time in milliseconds")
    max_wall_time_ms: int = Field(default=10000, description="Maximum wall time in milliseconds")
    default_timeout_ms: int = Field(default=5000, description="Default execution timeout in milliseconds")
    default_memory_limit_mb: int = Field(default=128, description="Default memory limit per container in MB")
    compilation_timeout_ms: int = Field(default=30000, description="Compilation timeout in milliseconds")
    
    # Container settings
    container_memory_limit: str = Field(default="512m", description="Docker memory limit")
    container_cpu_limit: str = Field(default="1", description="Docker CPU limit")
    container_cleanup_interval: int = Field(default=60, description="Cleanup interval in seconds")
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="JWT token expiration in minutes")
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts"
    )
    
    # Network settings
    enable_network: bool = Field(default=False, description="Enable network access in containers")
    
    # CORS settings
    enable_cors: bool = Field(default=True, description="Enable CORS")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed origins"
    )
    
    # Language image settings
    python3_image: str = Field(default="python:3.9-slim", description="Python 3 Docker image")
    javascript_image: str = Field(default="node:18-alpine", description="JavaScript Docker image")
    java_image: str = Field(default="openjdk:11-jdk-slim", description="Java Docker image")
    cpp_image: str = Field(default="gcc:latest", description="C++ Docker image")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
