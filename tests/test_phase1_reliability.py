import pytest
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from agent_am.config.settings import settings
from agent_am.database.models import PostType, PostStatus
from agent_am_growth.reliability.structured_logger import SecretMaskingFilter, structured_logger
from agent_am_growth.reliability.backup_manager import backup_manager
from agent_am_growth.reliability.retry_handler import retry_handler, TaskExecutionState
from agent_am_growth.reliability.idempotency import idempotency_guard
from agent_am_growth.reliability.health_checker import health_checker
from agent_am_growth.reliability.dispatcher import queue_dispatcher

def test_01_secret_masking():
    """خفیہ چابیوں اور کوکیز کی ماسکنگ کی جانچ"""
    raw_key = "AIzaSyB3_exampleFakeKey1234567890abcdef"
    masked = SecretMaskingFilter.mask_secrets(f"My key is {raw_key}")
    assert raw_key not in masked
    assert "****" in masked

    token_str = '{"token": "secret_oauth_token_val_12345"}'
    masked_token = SecretMaskingFilter.mask_secrets(token_str)
    assert "secret_oauth_token_val_12345" not in masked_token

def test_02_backup_creation_and_integrity():
    """آن لائن SQLite بیک اپ اور سالمیت کی جانچ"""
    res = backup_manager.create_backup(label="pytest_test")
    assert res["success"] is True
    assert os.path.exists(res["backup_path"])

    # سالمیت چیک
    is_valid, msg = backup_manager.verify_backup(res["backup_path"])
    assert is_valid is True
    assert msg == "OK"

def test_03_backup_restoration(tmp_path):
    """بیک اپ سے محفوظ بحالی کی جانچ"""
    b_res = backup_manager.create_backup(label="restore_test")
    assert b_res["success"] is True

    test_target = tmp_path / "restored_agent_test.db"
    r_res = backup_manager.restore_backup(b_res["backup_path"], target_db=str(test_target))
    assert r_res["success"] is True
    assert test_target.exists()

@pytest.mark.asyncio
async def test_04_idempotency_guard():
    """ڈپلیکیٹ اشاعت کی کڑی روک تھام کی جانچ"""
    # 1. 2026-10-16 کا کوئز پہلے ہی لائیو شائع ہو چکا ہے
    can_pub, reason = await idempotency_guard.can_publish(
        target_date="2026-10-16",
        post_type=PostType.QUIZ,
        content_hash="test_any_hash_123"
    )
    assert can_pub is False
    assert "پہلے ہی شائع" in reason

    # 2. مستقبل کی نئی تاریخ کا غیر شائع شدہ کوئز اجازت یافتہ ہونا چاہیے
    can_pub_new, _ = await idempotency_guard.can_publish(
        target_date="2030-01-01",
        post_type=PostType.QUIZ,
        content_hash="unique_future_hash_9999"
    )
    assert can_pub_new is True

@pytest.mark.asyncio
async def test_05_bounded_retries_with_backoff():
    """محدود ری ٹرائز اور ایکسپونینشل بیک آف کی جانچ"""
    attempts = 0

    async def failing_task():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionError("عارضی نیٹ ورک مسئلہ")
        return "SUCCESSFUL_RECOVERY"

    # عارضی خرابی کے بعد کامیابی
    state, res, err = await retry_handler.execute_with_retry(
        task_name="test_temp_failure",
        coro_fn=failing_task,
        max_retries=3
    )
    assert state == TaskExecutionState.SUCCESS
    assert res == "SUCCESSFUL_RECOVERY"
    assert attempts == 2

    # مسلسل ناکامی
    async def always_failing():
        raise ValueError("مسلسل خرابی")

    state_fail, res_fail, err_fail = await retry_handler.execute_with_retry(
        task_name="test_perm_failure",
        coro_fn=always_failing,
        max_retries=2
    )
    assert state_fail == TaskExecutionState.PERMANENT_FAILURE
    assert res_fail is None
    assert "مسلسل خرابی" in err_fail

@pytest.mark.asyncio
async def test_06_health_checker_components():
    """ہیلتھ مانیٹر کے اجزاء کی جانچ"""
    health = await health_checker.check_full_health()
    assert "components" in health
    assert "database" in health["components"]
    assert health["components"]["database"]["status"] == "HEALTHY"
    assert "browser_session" in health["components"]

@pytest.mark.asyncio
async def test_07_queue_dispatcher_dry_run():
    """ڈسپیچر کا محفوظ ڈرائے رن موڈ"""
    res = await queue_dispatcher.dispatch_due_posts(dry_run=True)
    assert "dispatched_count" in res
    assert "results" in res
