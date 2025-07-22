from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class LanguageEnum(str, Enum):
    PYTHON3 = "python3"
    PYTHON2 = "python2"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    RUBY = "ruby"
    PHP = "php"
    CSHARP = "csharp"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"


class SubmissionRequest(BaseModel):
    source_code: str = Field(..., max_length=65536, description="Source code to execute")
    language: LanguageEnum = Field(..., description="Programming language")
    stdin: Optional[str] = Field(None, max_length=4096, description="Standard input for the program")
    
    class Config:
        json_encoders = {
            LanguageEnum: lambda v: v.value
        }


class ExecutionResult(BaseModel):
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: Optional[int] = None
    memory_usage_kb: Optional[int] = None
    compile_output: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    language: LanguageEnum
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[ExecutionResult] = None
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            LanguageEnum: lambda v: v.value,
            JobStatus: lambda v: v.value
        }


class SubmissionResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    message: str = "Job submitted successfully"


# Language Configuration
LANGUAGE_CONFIG: Dict[LanguageEnum, Dict[str, Any]] = {
    LanguageEnum.PYTHON3: {
        "image": "python:3.9-slim",
        "compile_cmd": None,
        "run_cmd": ["python3", "/tmp/solution.py"],
        "file_extension": ".py",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.PYTHON2: {
        "image": "judge0/python2:latest",
        "compile_cmd": None,
        "run_cmd": ["python2", "/tmp/solution.py"],
        "file_extension": ".py",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.JAVA: {
        "image": "judge0/java:latest",
        "compile_cmd": ["javac", "/tmp/Solution.java"],
        "run_cmd": ["java", "-cp", "/tmp", "Solution"],
        "file_extension": ".java",
        "timeout": 10000,
        "memory_limit": 256
    },
    LanguageEnum.CPP: {
        "image": "gcc:latest",
        "compile_cmd": ["g++", "-o", "/tmp/solution", "/tmp/solution.cpp", "-std=c++17"],
        "run_cmd": ["/tmp/solution"],
        "file_extension": ".cpp",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.C: {
        "image": "gcc:latest",
        "compile_cmd": ["gcc", "-o", "/tmp/solution", "/tmp/solution.c"],
        "run_cmd": ["/tmp/solution"],
        "file_extension": ".c",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.JAVASCRIPT: {
        "image": "judge0/node:latest",
        "compile_cmd": None,
        "run_cmd": ["node", "/tmp/solution.js"],
        "file_extension": ".js",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.TYPESCRIPT: {
        "image": "judge0/typescript:latest",
        "compile_cmd": ["tsc", "/tmp/solution.ts", "--outDir", "/tmp"],
        "run_cmd": ["node", "/tmp/solution.js"],
        "file_extension": ".ts",
        "timeout": 8000,
        "memory_limit": 128
    },
    LanguageEnum.RUST: {
        "image": "judge0/rust:latest",
        "compile_cmd": ["rustc", "/tmp/solution.rs", "-o", "/tmp/solution"],
        "run_cmd": ["/tmp/solution"],
        "file_extension": ".rs",
        "timeout": 10000,
        "memory_limit": 128
    },
    LanguageEnum.GO: {
        "image": "judge0/go:latest",
        "compile_cmd": ["go", "build", "-o", "/tmp/solution", "/tmp/solution.go"],
        "run_cmd": ["/tmp/solution"],
        "file_extension": ".go",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.RUBY: {
        "image": "judge0/ruby:latest",
        "compile_cmd": None,
        "run_cmd": ["ruby", "/tmp/solution.rb"],
        "file_extension": ".rb",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.PHP: {
        "image": "judge0/php:latest",
        "compile_cmd": None,
        "run_cmd": ["php", "/tmp/solution.php"],
        "file_extension": ".php",
        "timeout": 5000,
        "memory_limit": 128
    },
    LanguageEnum.CSHARP: {
        "image": "judge0/csharp:latest",
        "compile_cmd": ["csc", "/tmp/solution.cs", "-out:/tmp/solution.exe"],
        "run_cmd": ["mono", "/tmp/solution.exe"],
        "file_extension": ".cs",
        "timeout": 8000,
        "memory_limit": 256
    }
}
