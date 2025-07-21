import redis
from rq import Queue, Worker
from typing import Any, Dict
import json

from shared.config import settings


class JobQueue:
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
        self.queue = Queue('execution', connection=self.redis_client)
    
    def enqueue_job(self, job_data: Dict[str, Any]) -> str:
        """Enqueue a job for execution"""
        job = self.queue.enqueue(
            'worker.executor.execute_code',
            job_data,
            timeout=30  # 30 seconds timeout for job processing
        )
        return job.id
    
    def get_job_status(self, job_id: str) -> str:
        """Get the status of a job"""
        job = self.queue.fetch_job(job_id)
        if job is None:
            return "not_found"
        return job.get_status()
    
    def get_job_result(self, job_id: str) -> Any:
        """Get the result of a completed job"""
        job = self.queue.fetch_job(job_id)
        if job is None:
            return None
        return job.result


# Global queue instance
job_queue = JobQueue()
