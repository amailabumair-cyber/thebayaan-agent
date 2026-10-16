import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel



from agent_am.config.settings import settings
from agent_am.database.connection import init_db, AsyncSessionLocal
from agent_am.database.models import ChannelConfig
from agent_am.services.scheduler_service import scheduler_service
from agent_am.core.commands import urdu_commands
from agent_am.core.queue_manager import queue_manager
from agent_am.core.workflow import workflow
from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # اسٹارٹ اپ لاجک
    print("Agent AM شروع ہو رہا ہے... ڈیٹا بیس ٹیبلز چیک کی جا رہی ہیں...")
    await init_db()
    # پس منظر شیڈولر اسٹارٹ کریں
    scheduler_service.start()
    print("خودکار بیک گراؤنڈ شیڈولر فعال ہو چکا ہے۔ (Asia/Karachi)")
    yield
    # شٹ ڈاؤن لاجک
    scheduler_service.shutdown()
    print("Agent AM بحفاظت بند ہو گیا۔")

app = FastAPI(
    title="Agent AM - Community Quiz & Poll Publisher",
    description="The Bayaan چینل کا خودکار کوئز اور پول مینیجر",
    version="1.0.0",
    lifespan=lifespan
)

# اسٹیٹک فائلز اور ٹیمپلیٹس ماؤنٹ کریں
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "agent_am" / "ui" / "static")), name="static")
app.mount("/reports", StaticFiles(directory=str(BASE_DIR / settings.REPORTS_DIR)), name="reports")
templates = Jinja2Templates(directory=str(BASE_DIR / "agent_am" / "ui" / "templates"))


class CommandRequest(BaseModel):
    command: str


class MobilePublishRequest(BaseModel):
    topic: Optional[str] = ""
    post_type: str = "QUIZ"  # "QUIZ" or "POLL"


@app.get("/mobile", response_class=HTMLResponse)
async def mobile_studio(request: Request):
    """موبائل فون براؤزر کے لیے خصوصی خودکار کنٹرول پینل"""
    return templates.TemplateResponse(
        request=request,
        name="mobile.html",
        context={
            "settings": settings,
            "channel_id": settings.CHANNEL_ID,
        }
    )


@app.post("/api/mobile/instant-publish")
async def api_mobile_instant_publish(req: MobilePublishRequest):
    """
    موبائل سے ایک لفظ کی ڈیمانڈ پر خودکار تخلیق، توثیق اور یوٹیوب پر لائیو اشاعت
    """
    import json
    import pytz
    from agent_am.services.ai_engine import ai_engine
    from agent_am.services.community_post_service import community_post_service
    from agent_am.database.models import PostType, PostStatus, PostQueue

    pkt = pytz.timezone(settings.TIMEZONE)
    now_pkt = datetime.now(pkt)
    target_date = now_pkt.strftime("%Y%m%d_%H%M%S")


    is_quiz = req.post_type.upper() == "QUIZ"
    p_type = PostType.QUIZ if is_quiz else PostType.POLL

    # 1. AI کے ذریعے موضوع پر سوال و 4 آپشنز کی تیاری
    if is_quiz:
        data = await ai_engine.generate_quiz(target_topic=req.topic.strip() or None)
    else:
        data = await ai_engine.generate_poll(target_topic=req.topic.strip() or None)

    question = data.get("question")
    options = data.get("options", [])
    correct_answer = data.get("correct_answer")
    explanation = data.get("explanation")
    source_ref = data.get("source_reference")

    # 2. ڈیٹابیس میں ریکارڈ اندراج
    async with AsyncSessionLocal() as session:
        queue_item = PostQueue(
            post_type=p_type,
            target_date=target_date,
            scheduled_time=now_pkt.replace(tzinfo=None),
            question_text=question,
            options_json=json.dumps(options, ensure_ascii=False),
            correct_answer=correct_answer,
            explanation=explanation,
            source_reference=source_ref,
            content_hash=data.get("content_hash", ""),
            status=PostStatus.VALIDATED,
        )
        session.add(queue_item)
        await session.commit()
        await session.refresh(queue_item)
        post_db_id = queue_item.id

    # 3. یوٹیوب پر براہِ راست اشاعت
    pub_res = await community_post_service.schedule_community_post(
        post_type=p_type,
        target_date=target_date,
        scheduled_time=now_pkt,
        question=question,
        options=options,
        correct_answer=correct_answer,
        explanation=explanation,
        source_reference=source_ref,
    )

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        stmt = select(PostQueue).where(PostQueue.id == post_db_id)
        saved = (await session.execute(stmt)).scalars().first()
        if saved:
            if pub_res.get("success"):
                saved.status = PostStatus.PUBLISHED
                saved.external_post_id = pub_res.get("external_id")
            else:
                saved.status = PostStatus.FAILED
                saved.last_error = pub_res.get("error")
            await session.commit()

    if not pub_res.get("success"):
        return JSONResponse(
            {"success": False, "error": pub_res.get("error", "اشاعت مکمل نہیں ہو سکی")},
            status_code=500,
        )

    # تازہ ترین اسکرین شاٹ کا پاتھ معلوم کریں
    screenshot_url = "/reports/poll_posted_live.png" if not is_quiz else "/reports/quiz_posted_live.png"
    reports_dir = Path(settings.REPORTS_DIR)
    submitted_files = sorted(
        list(reports_dir.glob("post_submitted_*.png")),
        key=os.path.getmtime,
        reverse=True,
    )
    if submitted_files:
        screenshot_url = f"/reports/{submitted_files[0].name}"

    return JSONResponse(
        {
            "success": True,
            "post_type": req.post_type,
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "source": source_ref,
            "external_id": pub_res.get("external_id"),
            "screenshot_url": screenshot_url,
        }
    )


@app.get("/", response_class=HTMLResponse)
async def home_studio(request: Request):
    """مرکزی اسٹوڈیو برائے کوئز اور پول خودکار اشاعت"""
    return templates.TemplateResponse(
        request=request,
        name="mobile.html",
        context={
            "settings": settings,
            "channel_id": settings.CHANNEL_ID,
        }
    )

@app.get("/console", response_class=HTMLResponse)
async def dashboard_console(request: Request):
    """ڈیسک ٹاپ مانیٹرنگ کنسول"""
    channel_info = {}
    async with AsyncSessionLocal() as session:
        stmt = select(ChannelConfig).where(ChannelConfig.channel_name == settings.CHANNEL_NAME)
        res = await session.execute(stmt)
        cfg = res.scalar_one_or_none()
        if cfg:
            channel_info = {
                "total_subscribers": f"{cfg.total_subscribers:,}",
                "total_views": f"{cfg.total_views:,}",
                "total_videos": cfg.total_videos
            }
        else:
            channel_info = {
                "total_subscribers": "48,500+",
                "total_views": "3,250,000+",
                "total_videos": "86"
            }

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "settings": settings,
            "channel": channel_info
        }
    )

@app.post("/api/command")
async def api_command(req: CommandRequest):
    """اردو کمانڈ ایگزیکیوشن اینڈپوائنٹ"""
    res = await urdu_commands.handle_command(req.command)
    return JSONResponse(res)

@app.get("/api/queue")
async def api_queue():
    """پوسٹنگ قطار لسٹ"""
    posts = await queue_manager.get_upcoming_queue(days_ahead=2)
    return JSONResponse({"posts": posts})

@app.post("/api/audit")
async def api_trigger_audit():
    """آڈٹ دستی طور پر ٹریگر کرنے کا اینڈپوائنٹ"""
    res = await workflow.execute_daily_workflow(is_manual=True)
    return JSONResponse(res)

@app.get("/api/health")
async def api_health():
    """سسٹم ہیلتھ اینڈپوائنٹ"""
    status = await urdu_commands.cmd_show_system_status()
    return JSONResponse(status)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
