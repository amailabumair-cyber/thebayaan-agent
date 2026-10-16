import os
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Agent AM کی مرکزی ترتیبات (System Configuration)
    تمام اہم متغیرات (Environment Variables) کو لوڈ اور مانیٹر کرتا ہے۔
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 1. بنیادی شناخت (Identity)
    AGENT_NAME: str = Field(default="Agent AM")
    CHANNEL_NAME: str = Field(default="The Bayan")
    CHANNEL_ID: str = Field(default="")
    TIMEZONE: str = Field(default="Asia/Karachi")

    # 2. شیڈولنگ کی ترتیبات (Scheduling Window)
    POSTING_WINDOW_START: str = Field(default="18:00")  # 6:00 PM PST
    POSTING_WINDOW_END: str = Field(default="21:00")    # 9:00 PM PST
    DAILY_AUDIT_TIME: str = Field(default="09:00")      # 9:00 AM PST
    SCHEDULING_HORIZON_HOURS: int = Field(default=48)   # 24-48 hours ahead

    # 3. ڈیٹا بیس (Database)
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./agent_am.db")

    # 4. اے آئی ماڈل (AI Settings)
    AI_PROVIDER: str = Field(default="gemini") # "gemini" or "openai"
    AI_MODEL_NAME: str = Field(default="gemini-3.8-flash")
    GEMINI_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")

    # 5. یوٹیوب انضمام (YouTube Integration)
    YOUTUBE_API_KEY: str = Field(default="")
    YOUTUBE_CLIENT_SECRET_FILE: str = Field(default="./client_secret.json")
    YOUTUBE_TOKEN_FILE: str = Field(default="./token.json")

    # 6. پبلشنگ موڈ (Publishing Mode)
    PUBLISH_MODE: str = Field(default="studio_automation") # "studio_automation", "manual_export", "api"
    HEADLESS_BROWSER: bool = Field(default=True)

    # 7. رپورٹس اور اطلاعات (Reports & Alerts)
    REPORTS_DIR: str = Field(default="./reports")
    ALERT_WEBHOOK_URL: str = Field(default="")

    # 8. سرور (Server)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(default="agent-am-secure-secret-key-the-bayan")

    @property
    def tz(self) -> ZoneInfo:
        """پاکستان ٹائم زون آبجیکٹ فراہم کرتا ہے"""
        try:
            return ZoneInfo(self.TIMEZONE)
        except Exception:
            return ZoneInfo("Asia/Karachi")

    def now(self) -> datetime:
        """پاکستان کے موجودہ وقت کے مطابق تاریخ اور وقت فراہم کرتا ہے"""
        return datetime.now(self.tz)

    def is_ai_configured(self) -> bool:
        """چیک کرتا ہے کہ آیا کم از کم ایک AI ماڈل کنفیگرڈ ہے"""
        if self.AI_PROVIDER.lower() == "gemini" and self.GEMINI_API_KEY:
            return True
        if self.AI_PROVIDER.lower() == "openai" and self.OPENAI_API_KEY:
            return True
        return False

    def is_youtube_configured(self) -> bool:
        """چیک کرتا ہے کہ آیا یوٹیوب ڈیٹا اے پی آئی کنفیگرڈ ہے"""
        return bool(self.YOUTUBE_API_KEY.strip())

settings = Settings()

# رپورٹس ڈائرکٹری کو یقینی بنائیں
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
