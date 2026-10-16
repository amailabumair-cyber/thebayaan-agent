import enum
import time
import random
import asyncio
import logging
from typing import Callable, Any, Dict, Optional, Tuple
from agent_am_growth.reliability.structured_logger import structured_logger

logger = logging.getLogger("agent_am.retry_handler")

class TaskExecutionState(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    RETRYING = "RETRYING"

class RetryHandler:
    """
    محدود ری ٹرائز اور ایکسپونینشل بیک آف ہینڈلر
    عارضی نیٹ ورک مسائل پر خودکار دوبارہ کوشش کرتا ہے اور بار بار ناکامی پر الرٹ دیتا ہے۔
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 2.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def calculate_backoff(self, attempt: int) -> float:
        """ایکسپونینشل بیک آف مع فل جٹر (Full Jitter) تاکہ سرور پر بیک وقت رش نہ بنے"""
        exponential = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        # Full jitter between 0.5 * delay and delay
        delay = random.uniform(exponential * 0.5, exponential)
        return round(delay, 2)

    async def execute_with_retry(
        self,
        task_name: str,
        coro_fn: Callable[..., Any],
        *args,
        max_retries: Optional[int] = None,
        on_permanent_failure: Optional[Callable[[str, Exception], Any]] = None,
        **kwargs
    ) -> Tuple[TaskExecutionState, Any, Optional[str]]:
        """
        کسی بھی async فنکشن کو محفوظ طریقے سے ری ٹرائی لاجک کے ساتھ چلاتا ہے
        """
        retries_limit = max_retries if max_retries is not None else self.max_retries
        last_error = None
        start_time = time.time()

        for attempt in range(1, retries_limit + 1):
            structured_logger.log_event(
                event_type="TASK_ATTEMPT",
                task_name=task_name,
                status=TaskExecutionState.RUNNING.value,
                details_urdu=f"کوشش نمبر {attempt}/{retries_limit} شروع کی گئی"
            )

            try:
                result = await coro_fn(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                structured_logger.log_event(
                    event_type="TASK_SUCCESS",
                    task_name=task_name,
                    status=TaskExecutionState.SUCCESS.value,
                    details_urdu=f"کام کامیابی سے مکمل ہوا (کوشش {attempt}/{retries_limit})",
                    duration_ms=duration_ms
                )
                return TaskExecutionState.SUCCESS, result, None

            except Exception as e:
                last_error = e
                duration_ms = int((time.time() - start_time) * 1000)

                if attempt < retries_limit:
                    delay_sec = self.calculate_backoff(attempt)
                    structured_logger.log_event(
                        event_type="TASK_RETRY",
                        task_name=task_name,
                        status=TaskExecutionState.RETRYING.value,
                        details_urdu=f"عارضی خرابی: {str(e)}۔ {delay_sec} سیکنڈ بعد اگلی کوشش...",
                        duration_ms=duration_ms,
                        error=str(e),
                        extra_data={"attempt": attempt, "next_delay": delay_sec}
                    )
                    await asyncio.sleep(delay_sec)
                else:
                    # تمام کوششیں ختم
                    structured_logger.log_event(
                        event_type="TASK_PERMANENT_FAILURE",
                        task_name=task_name,
                        status=TaskExecutionState.PERMANENT_FAILURE.value,
                        details_urdu=f"تمام {retries_limit} کوششیں ناکام ہو گئیں۔ مستقل ناکامی۔",
                        duration_ms=duration_ms,
                        error=str(e)
                    )

        if on_permanent_failure and last_error:
            try:
                if asyncio.iscoroutinefunction(on_permanent_failure):
                    await on_permanent_failure(task_name, last_error)
                else:
                    on_permanent_failure(task_name, last_error)
            except Exception as hook_err:
                logger.error(f"ناکام الرٹ ہک چلانے میں خرابی: {hook_err}")

        return TaskExecutionState.PERMANENT_FAILURE, None, str(last_error)

retry_handler = RetryHandler()
