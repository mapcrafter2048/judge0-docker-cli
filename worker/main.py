#!/usr/bin/env python3

import sys
import os
from rq import Queue, Connection, SimpleWorker
import redis

# Add the parent directory to the path so we can import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings
from shared.utils import setup_logging, get_logger

# Setup logging
setup_logging(settings.log_level)
logger = get_logger(__name__)


def main():
    """Main worker process"""
    try:
        # Connect to Redis
        redis_conn = redis.from_url(settings.redis_url)
        
        # Create queue
        queue = Queue('execution', connection=redis_conn)
        
        logger.info("Starting Judge0 worker...")
        logger.info(f"Connected to Redis at {settings.redis_url}")
        
        # Start worker - use SimpleWorker for Windows compatibility
        with Connection(redis_conn):
            # Use SimpleWorker which doesn't fork and works on Windows
            worker = SimpleWorker([queue], name=f'judge0-worker-{os.getpid()}')
            logger.info(f"Worker {worker.name} started successfully")
            worker.work()
            
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed to start: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
