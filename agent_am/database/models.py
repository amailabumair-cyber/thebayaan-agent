import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Enum,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class PostType(str, enum.Enum):
    QUIZ = "QUIZ"      # اسلامی تاریخ کوئز
    POLL = "POLL"      # معلوماتی ٹیکسٹ پول

class PostStatus(str, enum.Enum):
    DRAFT = "DRAFT"              # ابتدائی مسودہ تیار
    VALIDATED = "VALIDATED"      # تاریخی و شرعی حقائق کی تصدیق مکمل
    SCHEDULED = "SCHEDULED"      # یوٹیوب اسٹوڈیو میں شیڈول ہوچکا
    PUBLISHED = "PUBLISHED"      # کامیابی سے شائع ہوچکا
    FAILED = "FAILED"            # عمل ناکام رہا

class ChannelConfig(Base):
    """چینل کی بنیادی تصدیق اور معلومات"""
    __tablename__ = "channel_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_name = Column(String(255), nullable=False, default="The Bayan")
    channel_id = Column(String(100), nullable=True, unique=True)
    custom_url = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    total_subscribers = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_videos = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditReport(Base):
    """روزانہ کا مکمل آڈٹ ریکارڈ برائے 'The Bayan'"""
    __tablename__ = "audit_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(String(20), nullable=False, unique=True, index=True) # YYYY-MM-DD
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    total_views = Column(Integer, default=0)
    new_views_24h = Column(Integer, default=0)
    total_subscribers = Column(Integer, default=0)
    new_subscribers_24h = Column(Integer, default=0)
    total_videos = Column(Integer, default=0)
    
    # JSON اسٹرکچرڈ ڈیٹا (JSON Fields)
    top_performing_videos = Column(Text, default="[]")
    low_performing_videos = Column(Text, default="[]")
    recommendations_urdu = Column(Text, default="[]")
    
    summary_urdu = Column(Text, nullable=False)
    markdown_path = Column(String(500), nullable=True)
    html_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class VideoSnapshot(Base):
    """ویڈیوز کی انفرادی کارکردگی کا اسنیپ شاٹ"""
    __tablename__ = "video_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    published_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    snapshot_date = Column(String(20), nullable=False, index=True) # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)

class PostQueue(Base):
    """رولنگ 24 تا 48 گھنٹے پوسٹنگ قطار (Quizzes & Polls)"""
    __tablename__ = "post_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_type = Column(Enum(PostType), nullable=False) # QUIZ or POLL
    target_date = Column(String(20), nullable=False, index=True) # YYYY-MM-DD (Asia/Karachi)
    scheduled_time = Column(DateTime, nullable=False) # Planned ISO datetime
    
    question_text = Column(Text, nullable=False) # اردو میں سوال
    options_json = Column(Text, nullable=False) # فہرست آپشنز ["1", "2", "3", "4"]
    correct_answer = Column(String(255), nullable=True) # کوئز کا درست جواب
    explanation = Column(Text, nullable=True) # تفصیلی وضاحت
    source_reference = Column(Text, nullable=True) # تاریخی / معتبر حوالہ
    
    content_hash = Column(String(64), nullable=False, index=True) # تکرار روکنے کے لیے SHA256 ہیش
    status = Column(Enum(PostStatus), default=PostStatus.DRAFT, nullable=False, index=True)
    external_post_id = Column(String(100), nullable=True) # یوٹیوب کمیونٹی پوسٹ آئی ڈی
    
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ایک ہی تاریخ اور قسم کی ڈپلیکیٹ پوسٹ روکنے کے لیے کانسٹنٹ
    __table_args__ = (
        UniqueConstraint("target_date", "post_type", name="uq_target_date_post_type"),
    )

class ExecutionLog(Base):
    """سسٹم کے ہر کام اور جاب کا تفصیلی ریکارڈ"""
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100), nullable=False)
    task_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False) # RUNNING, SUCCESS, FAILED, RETRY
    duration_ms = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    details_urdu = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class SystemHealth(Base):
    """مختلف ماڈیولز کی لائیو ہیلتھ اور اسٹیٹس"""
    __tablename__ = "system_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    component = Column(String(100), nullable=False, unique=True)
    status = Column(String(50), nullable=False) # HEALTHY, DEGRADED, DOWN
    message_urdu = Column(Text, nullable=False)
    last_checked_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 2 — Growth Analytics Tables (additive only — existing tables unchanged)
# ---------------------------------------------------------------------------

class GrowthChannelSnapshot(Base):
    """چینل کی روزانہ کارکردگی کا تاریخی ریکارڈ (Phase 2 - Growth Analytics)"""
    __tablename__ = "growth_channel_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(String(20), nullable=False, unique=True, index=True)  # YYYY-MM-DD
    subscribers = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    # ڈیٹا کا ماخذ: live_api = براہ راست YouTube API | snapshot_db = پرانے DB سے لیا گیا
    data_source = Column(String(50), nullable=False, default="live_api")
    timestamp_pkt = Column(String(50), nullable=True)  # Asia/Karachi ISO timestamp
    created_at = Column(DateTime, default=datetime.utcnow)


class GrowthVideoSnapshot(Base):
    """ہر ویڈیو کی روزانہ کارکردگی کا تاریخی ریکارڈ (Phase 2 - Growth Analytics)"""
    __tablename__ = "growth_video_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    snapshot_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    duration_seconds = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("video_id", "snapshot_date", name="uq_video_date_snapshot"),
        Index("ix_growth_video_date", "snapshot_date"),
    )
