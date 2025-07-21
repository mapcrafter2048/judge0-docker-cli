"""Worker main module for Judge0 Docker CLI."""

import asyncio
import signal
import sys
from typing import Dict, Any

from shared.utils import get_logger
from shared.config import settings
from .executor import CodeExecutor

logger = get_logger(__name__)


class WorkerManager:
    """Manages worker processes for code execution."""
    
    def __init__(self):
        self.executor = CodeExecutor()
        self.running = False
    
    async def start(self):
        """Start the worker manager."""
        logger.info("Starting Worker Manager...")
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Worker Manager started with max {settings.max_workers} workers")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the worker manager."""
        logger.info("Stopping Worker Manager...")
        self.running = False
        logger.info("Worker Manager stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False
    
    async def execute_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single job."""
        try:
            return await asyncio.to_thread(self.executor.execute_code, job_data)
        except Exception as e:
            logger.error(f"Job execution failed: {e}")
            raise


async def main():
    """Main worker entry point."""
    logger.info("Judge0 Worker starting...")
    
    worker_manager = WorkerManager()
    
    try:
        await worker_manager.start()
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
