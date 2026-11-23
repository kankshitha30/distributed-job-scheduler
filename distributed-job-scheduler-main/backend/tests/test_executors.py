import pytest
from worker.executor import (
    EchoExecutor,
    SleepExecutor,
    EmailExecutor,
    CalculationExecutor,
    FailureExecutor,
    ExecutorRegistry,
)


@pytest.mark.asyncio
async def test_echo_executor():
    logs = []
    async def mock_log(level, msg):
        logs.append((level, msg))

    executor = ExecutorRegistry.get("echo")
    res = await executor.execute({"message": "Testing Echo"}, mock_log, attempt=1)
    assert res["echo"] == "Testing Echo"
    assert len(logs) == 1
    assert "Testing Echo" in logs[0][1]


@pytest.mark.asyncio
async def test_sleep_executor():
    logs = []
    async def mock_log(level, msg):
        logs.append((level, msg))

    executor = ExecutorRegistry.get("sleep")
    res = await executor.execute({"seconds": 0.05, "task_name": "quick_sleep"}, mock_log, attempt=1)
    assert res["slept_seconds"] == 0.05
    assert len(logs) == 2


@pytest.mark.asyncio
async def test_email_executor():
    logs = []
    async def mock_log(level, msg):
        logs.append((level, msg))

    executor = ExecutorRegistry.get("email_simulation")
    
    # Valid email
    res = await executor.execute({"to": "test@example.com", "subject": "Hello"}, mock_log, attempt=1)
    assert res["delivered"] is True
    assert res["to"] == "test@example.com"

    # Invalid email
    with pytest.raises(ValueError):
        await executor.execute({"to": "invalid-address"}, mock_log, attempt=1)


@pytest.mark.asyncio
async def test_calculation_executor():
    logs = []
    async def mock_log(level, msg):
        logs.append((level, msg))

    executor = ExecutorRegistry.get("calculation")
    
    # Fibonacci(10) = 55
    res_fib = await executor.execute({"operation": "fibonacci", "n": 10}, mock_log, attempt=1)
    assert res_fib["result"] == 55

    # Prime factors of 100 = [2, 2, 5, 5]
    res_prime = await executor.execute({"operation": "prime_factors", "n": 100}, mock_log, attempt=1)
    assert res_prime["result"] == [2, 2, 5, 5]


@pytest.mark.asyncio
async def test_failure_executor():
    logs = []
    async def mock_log(level, msg):
        logs.append((level, msg))

    executor = ExecutorRegistry.get("intentional_failure")

    # Should fail when attempt <= fail_times (e.g. attempt=1, fail_times=2)
    with pytest.raises(RuntimeError):
        await executor.execute({"fail_times": 2, "error": "Gateway Error"}, mock_log, attempt=1)

    # Should succeed when attempt > fail_times (e.g. attempt=3, fail_times=2)
    res = await executor.execute({"fail_times": 2, "error": "Gateway Error"}, mock_log, attempt=3)
    assert res["status"] == "recovered"
    assert res["attempt"] == 3
