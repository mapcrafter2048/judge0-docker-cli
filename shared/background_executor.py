"""
Background code execution using FastAPI's BackgroundTasks.
This replaces the RQ worker system for better Windows compatibility.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from shared.database import get_db, Job
from shared.models import JobStatus, LanguageEnum, LANGUAGE_CONFIG
from shared.utils import get_logger

logger = get_logger(__name__)


class BackgroundCodeExecutor:
    """Handles code execution in the background using FastAPI's Tasks"""

    def __init__(self):
        self.executor = None  # Lazy initialization
        self._active_jobs: Dict[str, bool] = {}

    def _ensure_executor(self):
        """Ensure the code executor is initialized"""
        if self.executor is None:
            try:
                from worker.executor import CodeExecutor
                self.executor = CodeExecutor()
                logger.info("Code executor initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize code executor: {e}")
                raise RuntimeError(f"Code executor initialization failed: {e}")
        return self.executor

    async def execute_code_job(self, job_id: str, source_code: str,
                               language: str, stdin: str = ""):
        """Execute code in the background and update job status"""
        try:
            # Mark job as active
            self._active_jobs[job_id] = True

            logger.info(f"Starting execution for job {job_id} "
                        f"in language {language}")

            # Update job status to PROCESSING
            await self._update_job_status(job_id, JobStatus.PROCESSING)

            # Parse language enum
            try:
                lang_enum = LanguageEnum(language)
            except ValueError:
                raise ValueError(f"Unsupported language: {language}")

            # Execute the code
            executor = self._ensure_executor()
            
            # Get language configuration
            lang_config = LANGUAGE_CONFIG[lang_enum]
            
            # Execute directly without job updates (we handle those here)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                executor._execute_in_container,
                source_code,
                lang_enum,
                lang_config,
                stdin
            )

            # Update job with results
            await self._update_job_with_results(job_id, result)

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {str(e)}")
            await self._update_job_error(job_id, str(e))

        finally:
            # Remove from active jobs
            self._active_jobs.pop(job_id, None)

    async def _update_job_status(self, job_id: str, status: JobStatus):
        """Update job status in database"""
        try:
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = status
                if status == JobStatus.PROCESSING:
                    job.started_at = datetime.utcnow()
                db.commit()
                logger.debug(f"Updated job {job_id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update job {job_id} status: {str(e)}")
        finally:
            db.close()

    async def _update_job_with_results(self, job_id: str,
                                       result: Dict[str, Any]):
        """Update job with execution results"""
        try:
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.stdout = result.get('stdout', '')
                job.stderr = result.get('stderr', '')
                job.exit_code = result.get('exit_code', 0)
                job.execution_time_ms = result.get('execution_time_ms', 0)
                job.memory_usage_kb = result.get('memory_usage_kb', 0)
                job.compile_output = result.get('compile_output', '')
                db.commit()
                logger.debug(f"Updated job {job_id} with results")
        except Exception as e:
            logger.error(f"Failed to update job {job_id} "
                         f"with results: {str(e)}")
        finally:
            db.close()

    async def _update_job_error(self, job_id: str, error_message: str):
        """Update job with error status"""
        try:
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.error_message = error_message
                db.commit()
                logger.debug(f"Updated job {job_id} with error: "
                             f"{error_message}")
        except Exception as e:
            logger.error(f"Failed to update job {job_id} with error: {str(e)}")
        finally:
            db.close()

    def is_job_active(self, job_id: str) -> bool:
        """Check if a job is currently being executed"""
        return job_id in self._active_jobs

    def get_active_jobs_count(self) -> int:
        """Get the number of currently active jobs"""
        return len(self._active_jobs)


# Global background executor instance
background_executor = BackgroundCodeExecutor()
