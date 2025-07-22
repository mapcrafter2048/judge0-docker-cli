import subprocess
import tempfile
import os
import time
import json
import uuid
import threading
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from shared.models import LANGUAGE_CONFIG, JobStatus, LanguageEnum
from shared.database import SessionLocal, Job
from shared.utils import get_logger
from shared.config import settings

logger = get_logger(__name__)


class CodeExecutor:
    def __init__(self, worker_id: int = None):
        # Convert MB to bytes for memory limit
        self.max_memory = f"{settings.max_memory_mb}m"
        # Convert ms to seconds
        self.max_cpu_time = settings.max_cpu_time_ms / 1000.0
        # Convert ms to seconds
        self.max_wall_time = settings.max_wall_time_ms / 1000.0
        # Track maximum memory usage during execution
        self.max_memory_used = 0
        # Worker identification
        self.worker_id = worker_id or os.getpid()

    def _get_container_memory_usage(self, container_name: str) -> int:
        """Get current memory usage of a container in KB"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format',
                '{{.MemUsage}}', container_name
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                mem_line = result.stdout.strip()
                # Parse memory usage (format: "used / limit")
                if '/' in mem_line:
                    used_str = mem_line.split('/')[0].strip()
                    # Convert to KB (handle MiB, GiB, KiB, B)
                    if 'MiB' in used_str:
                        value = float(used_str.replace('MiB', ''))
                        return int(value * 1024)
                    elif 'GiB' in used_str:
                        value = float(used_str.replace('GiB', ''))
                        return int(value * 1024 * 1024)
                    elif 'KiB' in used_str:
                        value = float(used_str.replace('KiB', ''))
                        return int(value)
                    elif 'B' in used_str and 'iB' not in used_str:
                        # Plain bytes
                        value = float(used_str.replace('B', ''))
                        return int(value / 1024)
                    else:
                        # Try to parse as number (fallback)
                        try:
                            return int(float(used_str) / 1024)
                        except ValueError:
                            pass
        except Exception as e:
            logger.debug(f"Failed to get memory usage for "
                        f"{container_name}: {e}")
        return 0

    def _monitor_container_memory(self, container_name: str, 
                                  monitoring_active: list) -> None:
        """Monitor container memory usage in background thread"""
        max_memory = 0
        while monitoring_active[0]:
            current_memory = self._get_container_memory_usage(container_name)
            if current_memory > max_memory:
                max_memory = current_memory
            time.sleep(0.1)  # Check every 100ms
        self.max_memory_used = max_memory

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
        
        # Update job status to processing with worker ID
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
        """Execute code in a Docker container using CLI"""
        
        # Create temporary directory for this execution
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write source code to file
            filename = self._get_filename(language, lang_config)
            source_file = os.path.join(temp_dir, filename)
            
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(source_code)
            
            # Create container name
            container_name = f"judge0_{uuid.uuid4().hex[:8]}"
            
            start_time = time.time()
            
            try:
                # Handle compilation if needed
                if lang_config.get('compile_cmd'):
                    compile_result = self._run_compilation(
                        temp_dir, lang_config, container_name + "_compile"
                    )
                    if compile_result['exit_code'] != 0:
                        return {
                            'status': JobStatus.COMPILATION_ERROR.value,
                            'stdout': '',
                            'stderr': compile_result['stderr'],
                            'exit_code': compile_result['exit_code'],
                            'execution_time': time.time() - start_time,
                            'memory_usage': 0
                        }
                
                # Build Docker run command for execution
                docker_cmd = [
                    'docker', 'run',
                    '--name', container_name,
                    '--interactive',
                    '--volume', f"{temp_dir}:/tmp",
                    '--workdir', '/tmp',
                    '--memory', self.max_memory,
                    '--cpus', '1',
                    '--network', 'none' if not settings.enable_network else 'bridge',
                    '--user', 'nobody',
                    lang_config['image']
                ] + lang_config['run_cmd']
                
                logger.info(f"Running Docker command: {' '.join(docker_cmd[:10])}...")
                
                # Execute container with timeout
                self.max_memory_used = 0
                monitoring_active = [True]
                
                # Start memory monitoring in background thread
                memory_thread = threading.Thread(
                    target=self._monitor_container_memory,
                    args=(container_name, monitoring_active)
                )
                memory_thread.daemon = True
                memory_thread.start()
                
                # Give container a moment to start before beginning execution
                time.sleep(0.2)
                
                process = subprocess.Popen(
                    docker_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=temp_dir
                )
                
                try:
                    stdout, stderr = process.communicate(
                        input=stdin,
                        timeout=self.max_wall_time
                    )
                    return_code = process.returncode
                    
                except subprocess.TimeoutExpired:
                    # Kill the process and container
                    process.kill()
                    monitoring_active[0] = False
                    self._cleanup_container(container_name)
                    return {
                        'status': JobStatus.TIMEOUT.value,
                        'stdout': '',
                        'stderr': 'Time limit exceeded',
                        'exit_code': 124,  # Standard timeout exit code
                        'execution_time': self.max_wall_time,
                        'memory_usage': self.max_memory_used
                    }
                
                # Stop memory monitoring
                monitoring_active[0] = False
                memory_thread.join(timeout=1)
                
                # Clean up container
                self._cleanup_container(container_name)
                
                execution_time = time.time() - start_time
                
                # Determine status based on exit code
                if return_code == 0:
                    status = JobStatus.COMPLETED.value
                else:
                    status = JobStatus.RUNTIME_ERROR.value
                
                # Prepare result
                result = {
                    'stdout': stdout or '',
                    'stderr': stderr or '',
                    'exit_code': return_code,
                    'execution_time': execution_time,
                    'memory_usage': self.max_memory_used,
                    'status': status
                }
                
                logger.info(f"Execution completed: exit_code={return_code}, "
                           f"time={execution_time:.3f}s, "
                           f"memory={self.max_memory_used}KB, "
                           f"stdout_len={len(stdout)}, stderr_len={len(stderr)}")
                
                return result
                
            except Exception as e:
                monitoring_active[0] = False
                self._cleanup_container(container_name)
                logger.error(f"Unexpected error during execution: {e}")
                return {
                    'status': JobStatus.FAILED.value,
                    'stdout': '',
                    'stderr': str(e),
                    'exit_code': 1,
                    'execution_time': time.time() - start_time,
                    'memory_usage': self.max_memory_used
                }

    def _run_compilation(
        self, temp_dir: str, lang_config: Dict[str, Any], container_name: str
    ) -> Dict[str, Any]:
        """Run compilation step for compiled languages"""
        
        docker_cmd = [
            'docker', 'run',
            '--name', container_name,
            '--rm',
            '--volume', f"{temp_dir}:/tmp",
            '--workdir', '/tmp',
            '--memory', self.max_memory,
            '--cpus', '1',
            '--network', 'none',
            '--user', 'nobody',
            lang_config['image']
        ] + lang_config['compile_cmd']
        
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=temp_dir
            )
            
            return {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            self._cleanup_container(container_name)
            return {
                'exit_code': 124,
                'stdout': '',
                'stderr': 'Compilation timeout'
            }
        except Exception as e:
            self._cleanup_container(container_name)
            return {
                'exit_code': 1,
                'stdout': '',
                'stderr': str(e)
            }
                
    def _cleanup_container(self, container_name: str):
        """Clean up container if it exists"""
        try:
            # First try to stop gracefully
            subprocess.run(['docker', 'stop', container_name],
                          capture_output=True, timeout=10)
            subprocess.run(['docker', 'rm', container_name],
                          capture_output=True, timeout=10)
        except Exception:
            # Force kill and remove if graceful stop fails
            try:
                subprocess.run(['docker', 'kill', container_name],
                              capture_output=True, timeout=5)
                subprocess.run(['docker', 'rm', container_name],
                              capture_output=True, timeout=5)
            except Exception:
                pass  # Container might already be gone

    def _get_filename(self, language: LanguageEnum, lang_config: Dict[str, Any]) -> str:
        """Get appropriate filename for the language"""
        extensions = {
            LanguageEnum.PYTHON3: 'solution.py',
            LanguageEnum.JAVASCRIPT: 'solution.js',
            LanguageEnum.JAVA: 'Solution.java',
            LanguageEnum.CPP: 'solution.cpp',
            LanguageEnum.C: 'solution.c',
            LanguageEnum.GO: 'solution.go',
            LanguageEnum.RUST: 'solution.rs',
            LanguageEnum.CSHARP: 'Solution.cs'
        }
        return extensions.get(language, 'solution.txt')

    def _update_job_status(self, job_id: str, status: JobStatus, 
                          error_message: str = None):
        """Update job status in database"""
        try:
            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = status
                    job.worker_id = self.worker_id
                    if error_message:
                        job.error_message = error_message
                    if status == JobStatus.PROCESSING:
                        job.started_at = datetime.utcnow()
                    job.updated_at = datetime.utcnow()
                    db.commit()
                    logger.debug(f"Updated job {job_id} status to {status} "
                               f"(worker {self.worker_id})")
                else:
                    logger.warning(f"Job {job_id} not found for status update")
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")

    def _update_job_result(self, job_id: str, result: Dict[str, Any]):
        """Update job with execution results"""
        try:
            with SessionLocal() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    # Convert string status to JobStatus enum
                    status_str = result.get('status', 'COMPLETED')
                    if status_str == 'completed':
                        job.status = JobStatus.COMPLETED
                    elif status_str == 'runtime_error':
                        job.status = JobStatus.RUNTIME_ERROR
                    elif status_str == 'timeout':
                        job.status = JobStatus.TIMEOUT
                    elif status_str == 'compilation_error':
                        job.status = JobStatus.COMPILATION_ERROR
                    else:
                        # Handle new uppercase enum values
                        try:
                            job.status = JobStatus(status_str)
                        except ValueError:
                            job.status = JobStatus.FAILED
                    
                    job.stdout = result.get('stdout', '')
                    job.stderr = result.get('stderr', '')
                    job.exit_code = result.get('exit_code', 0)
                    job.execution_time = result.get('execution_time', 0)
                    job.memory_usage = result.get('memory_usage', 0)
                    job.completed_at = datetime.utcnow()
                    job.updated_at = datetime.utcnow()
                    db.commit()
                    logger.debug(f"Updated job {job_id} with results")
                else:
                    logger.warning(f"Job {job_id} not found for result update")
        except Exception as e:
            logger.error(f"Failed to update job results: {e}")
