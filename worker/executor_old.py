import subprocess
import tempfile
import os
import time
import json
import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from shared.models import LANGUAGE_CONFIG, JobStatus, LanguageEnum
from shared.database import SessionLocal, Job
from shared.utils import get_logger
from shared.config import settings

logger = get_logger(__name__)


class CodeExecutor:
    def __init__(self):
        # Convert MB to bytes
        self.max_memory = settings.max_memory_mb * 1024 * 1024
        # Convert ms to seconds
        self.max_cpu_time = settings.max_cpu_time_ms / 1000.0
        # Convert ms to seconds
        self.max_wall_time = settings.max_wall_time_ms / 1000.0

    def _check_docker_available(self) -> bool:
        """Check if Docker is available using CLI"""
        try:
            result = subprocess.run(['docker', 'version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Docker not available: {e}")
            return False

    
    def execute_code(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution function"""
        job_id = job_data["job_id"]
        source_code = job_data["source_code"]
        language = LanguageEnum(job_data["language"])
        stdin = job_data.get("stdin", "")
        
        logger.info(f"Executing job {job_id} in language {language}")
        
        # Update job status to processing
        self._update_job_status(job_id, JobStatus.PROCESSING)
        
        try:
            # Check Docker availability
            if not self._check_docker_available():
                raise RuntimeError("Docker is not available")
            
            # Get language configuration
            lang_config = LANGUAGE_CONFIG[language]
            
            # Execute the code
            result = self._execute_in_container(
                source_code, language, lang_config, stdin
            )
            
            # Update job with results
            self._update_job_result(job_id, result)
            
            logger.info(f"Job {job_id} completed successfully")
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job_id} failed: {error_msg}")
            self._update_job_status(job_id, JobStatus.FAILED, error_msg)
            raise
    
    def _execute_in_container(
        self, 
        source_code: str, 
        language: LanguageEnum, 
        lang_config: Dict[str, Any], 
        stdin: str
    ) -> Dict[str, Any]:
        """Execute code in a Docker container"""
        
        # Create temporary directory for this execution
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write source code to file
            filename = self._get_filename(language, lang_config)
            source_file = os.path.join(temp_dir, filename)
            
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(source_code)
            
            # Prepare container configuration
            # Convert Windows path to Unix-style for Docker
            volume_path = temp_dir.replace('\\', '/')
            if volume_path[1] == ':':  # Windows drive letter
                volume_path = f"/{volume_path[0].lower()}{volume_path[2:]}"
            
            container_config = {
                'image': lang_config['image'],
                'volumes': {temp_dir: {'bind': '/tmp', 'mode': 'rw'}},
                'working_dir': '/tmp',
                'network_mode': 'none' if not settings.enable_network else 'bridge',
                'mem_limit': self.max_memory,
                'memswap_limit': self.max_memory,
                'cpu_period': 100000,
                'cpu_quota': int(100000 * 1),  # 1 CPU
                # Remove user restriction for now to avoid permission issues
                # 'user': 'nobody',
                'remove': True,
                'detach': True,
                'stdin_open': True,
                'tty': False
            }
            
            start_time = time.time()
            
            try:
                # Handle compilation if needed
                if lang_config['compile_cmd']:
                    compile_result = self._run_compilation(container_config, lang_config)
                    if compile_result['exit_code'] != 0:
                        return {
                            'status': JobStatus.COMPILATION_ERROR,
                            'compile_output': compile_result['stderr'],
                            'execution_time_ms': int((time.time() - start_time) * 1000)
                        }
                
                # Execute the program
                execution_result = self._run_execution(container_config, lang_config, stdin)
                
                end_time = time.time()
                execution_time_ms = int((end_time - start_time) * 1000)
                
                # Check for timeout
                if execution_time_ms > settings.max_wall_time_ms:
                    return {
                        'status': JobStatus.TIMEOUT,
                        'execution_time_ms': execution_time_ms,
                        'error_message': f'Execution exceeded {settings.max_wall_time_ms}ms limit'
                    }
                
                # Determine final status
                if execution_result['exit_code'] != 0:
                    status = JobStatus.RUNTIME_ERROR
                else:
                    status = JobStatus.COMPLETED
                
                return {
                    'status': status,
                    'stdout': execution_result['stdout'],
                    'stderr': execution_result['stderr'],
                    'exit_code': execution_result['exit_code'],
                    'execution_time_ms': execution_time_ms,
                    'memory_usage_kb': execution_result.get('memory_usage_kb', 0)
                }
                
            except docker.errors.ContainerError as e:
                return {
                    'status': JobStatus.RUNTIME_ERROR,
                    'stderr': str(e),
                    'exit_code': e.exit_status,
                    'execution_time_ms': int((time.time() - start_time) * 1000)
                }
            except Exception as e:
                return {
                    'status': JobStatus.FAILED,
                    'error_message': str(e),
                    'execution_time_ms': int((time.time() - start_time) * 1000)
                }
    
    def _run_compilation(self, container_config: Dict, lang_config: Dict) -> Dict[str, Any]:
        """Run compilation step for compiled languages"""
        compile_container_config = container_config.copy()
        compile_container_config['command'] = lang_config['compile_cmd']
        
        try:
            container = self.docker_client.containers.run(**compile_container_config)
            
            # Wait for compilation to complete
            result = container.wait(timeout=30)
            logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='ignore')
            
            return {
                'exit_code': result['StatusCode'],
                'stdout': logs,
                'stderr': logs if result['StatusCode'] != 0 else ""
            }
            
        except docker.errors.ContainerError as e:
            return {
                'exit_code': e.exit_status,
                'stdout': "",
                'stderr': e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
            }
    
    def _run_execution(self, container_config: Dict, lang_config: Dict, stdin: str) -> Dict[str, Any]:
        """Run the actual program execution"""
        exec_container_config = container_config.copy()
        exec_container_config['command'] = lang_config['run_cmd']
        
        # Use simple synchronous execution - this should work better
        exec_container_config['remove'] = True  # Auto-remove when done
        exec_container_config['detach'] = False  # Synchronous execution
        
        try:
            # Simple approach: run container synchronously and capture output
            logger.debug(f"Running container with config: {exec_container_config}")
            
            output = self.docker_client.containers.run(**exec_container_config)
            
            # For synchronous runs, output is the stdout bytes
            stdout = output.decode('utf-8', errors='ignore') if output else ""
            stderr = ""
            exit_code = 0
            
            logger.debug(f"Container execution completed. stdout length: {len(stdout)}")
            
        except docker.errors.ContainerError as e:
            # Container ran but exited with non-zero status
            stdout = ""
            stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
            exit_code = e.exit_status
            logger.debug(f"Container error: exit_code={exit_code}, stderr={stderr}")
            
        except Exception as e:
            # Other errors (connection, etc.)
            stdout = ""
            stderr = f"Execution error: {str(e)}"
            exit_code = 1
            logger.error(f"Unexpected error during execution: {str(e)}")
        
        return {
            'exit_code': exit_code,
            'stdout': stdout,
            'stderr': stderr,
            'memory_usage_kb': 0  # TODO: Implement memory monitoring
        }
    
    def _get_filename(self, language: LanguageEnum, lang_config: Dict) -> str:
        """Get the appropriate filename for the language"""
        if language == LanguageEnum.JAVA:
            return "Solution.java"  # Java requires specific class name
        else:
            return f"solution{lang_config['file_extension']}"
    
    def _update_job_status(self, job_id: str, status: JobStatus, error_message: str = None):
        """Update job status in database"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = status
                if error_message:
                    job.error_message = error_message
                if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT, 
                            JobStatus.COMPILATION_ERROR, JobStatus.RUNTIME_ERROR]:
                    job.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
    
    def _update_job_result(self, job_id: str, result: Dict[str, Any]):
        """Update job with execution results"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = result['status']
                job.stdout = result.get('stdout')
                job.stderr = result.get('stderr')
                job.exit_code = result.get('exit_code')
                job.execution_time_ms = result.get('execution_time_ms')
                job.memory_usage_kb = result.get('memory_usage_kb')
                job.compile_output = result.get('compile_output')
                job.error_message = result.get('error_message')
                job.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()


# Function for RQ worker
def execute_code(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point for RQ worker"""
    executor = CodeExecutor()
    return executor.execute_code(job_data)
