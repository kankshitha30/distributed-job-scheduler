import abc
import asyncio
import time
from typing import Dict, Any, Callable, Awaitable, Type


class JobExecutor(abc.ABC):
    """Abstract Base Class for all Job Handlers."""

    @abc.abstractmethod
    async def execute(
        self,
        payload: Dict[str, Any],
        log_fn: Callable[[str, str], Awaitable[None]],
        attempt: int = 1,
    ) -> Dict[str, Any]:
        """
        Executes the job logic.
        :param payload: JSON dict payload supplied during job creation.
        :param log_fn: Async logging function `log_fn(level, message)`.
        :param attempt: Current attempt count.
        :return: Result dictionary or summary.
        :raises Exception: On job execution failure.
        """
        pass


class EchoExecutor(JobExecutor):
    """Echoes input payload back into logs."""

    async def execute(
        self,
        payload: Dict[str, Any],
        log_fn: Callable[[str, str], Awaitable[None]],
        attempt: int = 1,
    ) -> Dict[str, Any]:
        msg = payload.get("message", "No message provided")
        await log_fn("INFO", f"Echoing message: {msg} (attempt {attempt})")
        return {"echo": msg, "payload": payload}


class SleepExecutor(JobExecutor):
    """Simulates long-running background tasks with asynchronous sleep."""

    async def execute(
        self,
        payload: Dict[str, Any],
        log_fn: Callable[[str, str], Awaitable[None]],
        attempt: int = 1,
    ) -> Dict[str, Any]:
        seconds = float(payload.get("seconds", 2))
        task_name = payload.get("task_name", "generic_sleep")
        await log_fn("INFO", f"Starting sleep task '{task_name}' for {seconds}s (attempt {attempt})")
        await asyncio.sleep(seconds)
        await log_fn("INFO", f"Finished sleep task '{task_name}' successfully")
        return {"slept_seconds": seconds, "task_name": task_name}


class EmailExecutor(JobExecutor):
    """Simulates sending transactional emails with validation."""

    async def execute(
        self,
        payload: Dict[str, Any],
        log_fn: Callable[[str, str], Awaitable[None]],
        attempt: int = 1,
    ) -> Dict[str, Any]:
        to_email = payload.get("to")
        subject = payload.get("subject", "No subject")
        template = payload.get("template", "default")

        if not to_email or "@" not in to_email:
            await log_fn("ERROR", f"Invalid recipient email address: '{to_email}'")
            raise ValueError(f"Invalid email address: {to_email}")

        await log_fn("INFO", f"Connecting to simulated SMTP server for recipient: {to_email}")
        await asyncio.sleep(0.5)  # Simulate network latency
        await log_fn("INFO", f"Delivered email '{subject}' with template '{template}' to {to_email}")
        return {"delivered": True, "to": to_email, "subject": subject}


class CalculationExecutor(JobExecutor):
    """Performs CPU or mathematical calculations (Fibonacci, primes, summation)."""

    async def execute(
        self,
        payload: Dict[str, Any],
        log_fn: Callable[[str, str], Awaitable[None]],
        attempt: int = 1,
    ) -> Dict[str, Any]:
        operation = payload.get("operation", "fibonacci")
        n = int(payload.get("n", 30))

        await log_fn("INFO", f"Starting calculation '{operation}' with n={n}")
        start_t = time.perf_counter()

        if operation == "fibonacci":
            n = min(n, 40)  # Bound n to prevent extreme stalls
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            result = a
        elif operation == "prime_factors":
            n = min(n, 10_000_000)
            factors = []
            d = 2
            temp = n
            while d * d <= temp:
                while (temp % d) == 0:
                    factors.append(d)
                    temp //= d
                d += 1
            if temp > 1:
                factors.append(temp)
            result = factors
        else:
            result = sum(range(n + 1))

        calc_ms = round((time.perf_counter() - start_t) * 1000, 2)
        await log_fn("INFO", f"Completed calculation '{operation}' in {calc_ms}ms with result: {result}")
        return {"operation": operation, "n": n, "result": result, "calc_ms": calc_ms}


class FailureExecutor(JobExecutor):
    """
    Intentionally fails to demonstrate retries, exponential backoffs, and Dead Letter Queues.
    Configurable with `fail_times` to succeed after N attempts or fail indefinitely.
    """

    async def execute(
        self,
        payload: Dict[str, Any],
        log_fn: Callable[[str, str], Awaitable[None]],
        attempt: int = 1,
    ) -> Dict[str, Any]:
        error_message = payload.get("error", "Intentional simulated failure for testing DLQ/retry")
        fail_times = int(payload.get("fail_times", 999))  # Default fail always

        await log_fn("WARN", f"Executing FailureExecutor attempt #{attempt} (fail_times={fail_times})")

        if attempt <= fail_times:
            await log_fn("ERROR", f"Simulated failure triggered on attempt {attempt}: {error_message}")
            raise RuntimeError(f"Attempt {attempt} failed: {error_message}")

        await log_fn("INFO", f"Job succeeded on attempt {attempt} after {fail_times} intended failures!")
        return {"status": "recovered", "attempt": attempt}


class ExecutorRegistry:
    """Registry maintaining available job executor classes."""

    _executors: Dict[str, JobExecutor] = {
        "echo": EchoExecutor(),
        "sleep": SleepExecutor(),
        "email_simulation": EmailExecutor(),
        "email": EmailExecutor(),
        "calculation": CalculationExecutor(),
        "intentional_failure": FailureExecutor(),
    }

    @classmethod
    def get(cls, job_type: str) -> JobExecutor:
        executor = cls._executors.get(job_type.lower())
        if not executor:
            # Fallback to EchoExecutor for unknown types
            return cls._executors["echo"]
        return executor

    @classmethod
    def register(cls, job_type: str, executor: JobExecutor):
        cls._executors[job_type.lower()] = executor
