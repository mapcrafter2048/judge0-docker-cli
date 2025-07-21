import os
import sys
import pytest

# Ensure project root is in sys.path when running tests directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.queue import JobQueue


def test_job_queue_connection_params():
    queue = JobQueue()
    conn_kwargs = queue.redis_client.connection_pool.connection_kwargs
    assert conn_kwargs.get('host') == 'localhost'
    assert conn_kwargs.get('port') == 6379
    assert conn_kwargs.get('db') == 0
