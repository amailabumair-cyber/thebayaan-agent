import pytest
import os
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from agent_am.config.settings import settings
from agent_am.database.connection import init_db, AsyncSessionLocal
from agent_am.services.ai_engine import ai_engine
from agent_am.services.youtube_service import youtube_service
from agent_am.services.audit_service import audit_service
from agent_am.services.report_generator import report_generator
from agent_am.core.queue_manager import queue_manager
from agent_am.core.commands import urdu_commands
from agent_am.core.workflow import workflow

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_01_timezone_and_settings():
    """ٹائم زون اور کنفیگریشن کی درستگی کی جانچ"""
    assert settings.TIMEZONE == "Asia/Karachi"
    assert settings.AGENT_NAME == "Agent AM"
    assert settings.CHANNEL_NAME == "The Bayan"
    now_pkt = settings.now()
    assert now_pkt.tzinfo == ZoneInfo("Asia/Karachi")

@pytest.mark.asyncio
async def test_02_database_initialization():
    """ڈیٹا بیس ٹیبلز کے قیام کی جانچ"""
    await init_db()
    assert os.path.exists("./agent_am.db") or "sqlite" in settings.DATABASE_URL

@pytest.mark.asyncio
async def test_03_youtube_service():
    """یوٹیوب ڈیٹا سروس اور چینل تفصیلات کی جانچ"""
    ch = await youtube_service.get_channel_details()
    assert ch is not None
    assert "subscribers" in ch
    assert "views" in ch
    videos = await youtube_service.get_recent_videos()
    assert len(videos) > 0
    assert "title" in videos[0]

@pytest.mark.asyncio
async def test_04_ai_quiz_generation_and_validation():
    """اسلامی تاریخ کوئز کی تیاری، شرائط اور تصدیق کی جانچ"""
    quiz = await ai_engine.generate_quiz()
    assert "question" in quiz
    assert len(quiz["options"]) >= 2
    assert "correct_answer" in quiz
    assert quiz["correct_answer"] in quiz["options"]
    assert "source_reference" in quiz
    assert "content_hash" in quiz

@pytest.mark.asyncio
async def test_05_ai_poll_generation_and_validation():
    """ٹیکسٹ پول کی تیاری اور آپشنز کی جانچ"""
    poll = await ai_engine.generate_poll()
    assert "question" in poll
    assert len(poll["options"]) >= 2
    assert "content_hash" in poll

@pytest.mark.asyncio
async def test_06_queue_replenishment_and_duplicate_prevention():
    """رولنگ 24-48 گھنٹے پوسٹنگ قطار اور ڈپلیکیٹ کی روک تھام کی جانچ"""
    res1 = await queue_manager.replenish_queue(days_ahead=2)
    assert res1["status"] == "success"
    
    # دوبارہ چلانے پر نئی ڈپلیکیٹ پوسٹ شامل نہیں ہونی چاہیے
    res2 = await queue_manager.replenish_queue(days_ahead=2)
    assert res2["generated_count"] == 0

    upcoming = await queue_manager.get_upcoming_queue(days_ahead=2)
    assert len(upcoming) >= 2 # کم از کم ایک کوئز اور ایک پول

@pytest.mark.asyncio
async def test_07_audit_and_urdu_report_generation():
    """یومیہ آڈٹ اور اردو مارک ڈاؤن و ایچ ٹی ایم ایل رپورٹ جنریشن کی جانچ"""
    audit_data = await audit_service.perform_daily_audit()
    assert audit_data["report_date"] is not None
    assert "top_videos" in audit_data

    upcoming = await queue_manager.get_upcoming_queue(days_ahead=2)
    report_res = await report_generator.generate_and_save_report(
        audit_data=audit_data,
        upcoming_posts=upcoming
    )
    assert os.path.exists(report_res["markdown_path"])
    assert os.path.exists(report_res["html_path"])
    
    # رپورٹ کا مواد چیک کریں کہ اردو میں ہے
    with open(report_res["markdown_path"], "r", encoding="utf-8") as f:
        content = f.read()
        assert "The Bayan" in content
        assert "خلاصہ" in content or "آڈٹ رپورٹ" in content

@pytest.mark.asyncio
async def test_08_urdu_commands():
    """اردو کمانڈ انٹرفیس کی جانچ"""
    res = await urdu_commands.handle_command("ایجنٹ کا سسٹم اسٹیٹس دکھائیں")
    assert res["success"] is True
    assert "Agent AM" in res["message_urdu"]

    res_posts = await urdu_commands.handle_command("اگلے دو دن کی پوسٹس دکھائیں")
    assert res_posts["success"] is True
    assert "posts" in res_posts

@pytest.mark.asyncio
async def test_09_full_autonomous_workflow():
    """مکمل یومیہ خودکار ورک فلو کی اینڈ ٹو اینڈ جانچ"""
    flow_res = await workflow.execute_daily_workflow(is_manual=True)
    assert flow_res["status"] in ["SUCCESS", "WARNING"]
    assert flow_res["report_date"] is not None

def test_10_fastapi_web_dashboard():
    """ویب ڈیش بورڈ اور API اینڈپوائنٹس کی جانچ"""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Agent AM" in resp.text

    q_resp = client.get("/api/queue")
    assert q_resp.status_code == 200
    assert "posts" in q_resp.json()
