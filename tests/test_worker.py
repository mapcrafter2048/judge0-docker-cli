from worker.executor import CodeExecutor


def test_execute_code(monkeypatch):
    executor = CodeExecutor()

    sample_job = {
        "job_id": "job1",
        "source_code": 'print("hi")',
        "language": "python3",
        "stdin": "",
    }

    expected = {
        "stdout": "hi\n",
        "stderr": "",
        "exit_code": 0,
        "execution_time": 0.1,
        "memory_usage": 0,
        "status": "completed",
    }

    monkeypatch.setattr(executor, "_check_docker_available", lambda: True)
    monkeypatch.setattr(
        executor,
        "_execute_in_container",
        lambda *args, **kwargs: expected,
    )
    monkeypatch.setattr(
        executor,
        "_update_job_status",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        executor,
        "_update_job_result",
        lambda *args, **kwargs: None,
    )

    result = executor.execute_code(sample_job)
    assert result == expected
