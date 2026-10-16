import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
from agent_am_growth.dashboard import growth_router
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
    title="Agent AM - Autonomous YouTube Channel Manager",
    description="The Bayan چینل کا خودکار اے آئی مینیجر",
    version="1.0.0",
    lifespan=lifespan
)

# اسٹیٹک فائلز اور ٹیمپلیٹس ماؤنٹ کریں
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "agent_am" / "ui" / "static")), name="static")
app.mount("/reports", StaticFiles(directory=str(BASE_DIR / settings.REPORTS_DIR)), name="reports")
templates = Jinja2Templates(directory=str(BASE_DIR / "agent_am" / "ui" / "templates"))

# Phase 6 — یوٹیوب گروتھ سسٹم کے توسیعی روٹس
app.include_router(growth_router)


class CommandRequest(BaseModel):
    command: str

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """مرکزی اردو ڈیش بورڈ"""
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
