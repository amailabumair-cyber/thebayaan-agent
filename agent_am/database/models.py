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
    QUIZ = "QUIZ"              # اسلامی تاریخ کوئز (4 آپشنز مع صحیح جواب)
    POLL = "POLL"              # ٹیکسٹ پول
    TEXT_POLL = "TEXT_POLL"    # ٹیکسٹ پول (4 آپشنز)
    IMAGE = "IMAGE"            # تصویر پوسٹ (معلوماتی تصویر مع کیپشن)
    IMAGE_POLL = "IMAGE_POLL"  # تصویر پول (2 تا 4 آپشنز مع تصاویر)

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
    image_path = Column(String(500), nullable=True) # تصویری پوسٹ کی فائل کا پاتھ
    images_json = Column(Text, nullable=True) # تصویر پول کے آپشنز کی تصاویر کا JSON ["path1", "path2", ...]
    
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


# ---------------------------------------------------------------------------
# Phase 3 — Content Intelligence Tables (additive only — existing tables unchanged)
# ---------------------------------------------------------------------------

class ContentCategory(str, enum.Enum):
    PROPHETS = "PROPHETS"              # قصص الانبیاء
    SEERAH = "SEERAH"                  # سیرت النبی ﷺ اور ابتدائی اسلامی تاریخ
    COMPANIONS = "COMPANIONS"          # خلفائے راشدین اور صحابہ کرام
    BATTLES_EVENTS = "BATTLES_EVENTS"  # تاریخی معرکے اور اہم واقعات
    AUDIENCE_QA = "AUDIENCE_QA"        # سامعین کے تعلیمی سوالات و جوابات


class ProposalStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"              # تجویز شدہ
    APPROVED = "APPROVED"              # منظور شدہ
    REJECTED = "REJECTED"              # مسترد
    PRODUCED = "PRODUCED"              # پروڈکشن میں شامل


class ContentTopicProposal(Base):
    """ویڈیو اور کمیونٹی موضوعات کی تجاویز (Phase 3 - Content Intelligence)"""
    __tablename__ = "content_topic_proposals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(Enum(ContentCategory), nullable=False, index=True)
    topic_title_urdu = Column(String(500), nullable=False)
    suggested_titles_json = Column(Text, nullable=False, default="[]")  # 3 titles
    opening_hook_urdu = Column(Text, nullable=False)                    # 15s hook
    thumbnail_concept_urdu = Column(Text, nullable=False)               # Visual thumbnail concept
    priority_score = Column(Integer, default=50)                        # 1-100 score
    rationale_urdu = Column(Text, nullable=False)                       # کیوں ضروری ہے
    uncertainty_notes_urdu = Column(Text, nullable=False)               # حدود اور غیر یقینی
    content_fingerprint = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256
    status = Column(Enum(ProposalStatus), default=ProposalStatus.PROPOSED, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContentCalendarEntry(Base):
    """30 روزہ جامع کونٹینٹ کیلنڈر (Phase 3 - Content Intelligence)"""
    __tablename__ = "content_calendar_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day_number = Column(Integer, nullable=False, unique=True, index=True)  # 1 to 30
    target_date = Column(String(20), nullable=False, unique=True, index=True)  # YYYY-MM-DD (PKT)
    category = Column(Enum(ContentCategory), nullable=False)
    video_topic_id = Column(Integer, nullable=True)                     # ContentTopicProposal ID
    video_title_urdu = Column(String(500), nullable=False)
    quiz_proposal_urdu = Column(Text, nullable=False)                   # شام 6:15 کا کوئز
    poll_proposal_urdu = Column(Text, nullable=False)                   # رات 8:15 کا پول
    production_priority = Column(String(20), default="MEDIUM")          # HIGH, MEDIUM, LOW
    notes_urdu = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 4 — Audience Manager Tables (additive only — existing tables unchanged)
# ---------------------------------------------------------------------------

class CommentSentiment(str, enum.Enum):
    POSITIVE = "POSITIVE"      # تحسین و دعا
    QUESTION = "QUESTION"      # سوال یا استفسار
    REQUEST = "REQUEST"        # موضوع کی فرمائش
    CONFUSION = "CONFUSION"    # ابہام یا تاریخی اشکال
    NEUTRAL = "NEUTRAL"        # عام تبصرہ


class DraftReplyStatus(str, enum.Enum):
    DRAFT_ONLY = "DRAFT_ONLY"            # صرف مسودہ (خودکار شائع نہیں ہوگا)
    APPROVED_FOR_MANUAL = "APPROVED"     # دستی کاپی کے لیے منظور شدہ
    REJECTED = "REJECTED"                # مسترد


class AudienceComment(Base):
    """یوٹیوب ویڈیوز کے کمنٹس اور تجزیہ (Phase 4 - Audience Manager)"""
    __tablename__ = "audience_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(String(100), nullable=False, unique=True, index=True)
    author_name = Column(String(255), nullable=False)
    author_channel_id = Column(String(100), nullable=True)
    text_original = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=True)
    like_count = Column(Integer, default=0)
    video_id = Column(String(100), nullable=True, index=True)

    sentiment = Column(Enum(CommentSentiment), default=CommentSentiment.NEUTRAL, nullable=False)
    is_question = Column(Boolean, default=False)
    draft_reply_urdu = Column(Text, nullable=True)
    draft_status = Column(Enum(DraftReplyStatus), default=DraftReplyStatus.DRAFT_ONLY, nullable=False)

    retrieved_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 5 — Video Production Pipeline Tables (additive only — existing tables unchanged)
# ---------------------------------------------------------------------------

class ProductionStage(str, enum.Enum):
    TOPIC_PROPOSED = "TOPIC_PROPOSED"              # 1. موضوع تجویز شدہ
    RESEARCH_PENDING = "RESEARCH_PENDING"          # 2. تحقیق طلب
    SOURCES_REVIEWED = "SOURCES_REVIEWED"          # 3. مآخذ و روایات کی جانچ مکمل
    SCRIPT_DRAFT = "SCRIPT_DRAFT"                  # 4. ابتدائی اسکرپٹ تحریر
    SCRIPT_APPROVED = "SCRIPT_APPROVED"            # 5. اسکرپٹ کی شرعی و تاریخی منظوری
    VISUAL_PROMPTS = "VISUAL_PROMPTS"              # 6. منظر بہ منظر بصری پرامپٹس تیار
    VOICEOVER_EDITING = "VOICEOVER_EDITING"        # 7. صداکاری و ویڈیو ایڈیٹنگ
    UPLOAD_PREP = "UPLOAD_PREP"                    # 8. عنوان، تفصیل، ٹیگز اور تھمب نیل تیار
    PUBLICATION_APPROVED = "PUBLICATION_APPROVED"  # 9. اشاعت کی حتمی منظوری
    PERFORMANCE_REVIEW = "PERFORMANCE_REVIEW"      # 10. کارکردگی کا تفصیلی جائزہ


class VideoProductionProject(Base):
    """10 مراحل پر مشتمل ویڈیو پروڈکشن پائپ لائن (Phase 5 - Video Production Manager)"""
    __tablename__ = "video_production_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_code = Column(String(50), nullable=False, unique=True, index=True)  # مثلاً VPP-001
    title_urdu = Column(String(500), nullable=False)
    stage = Column(Enum(ProductionStage), default=ProductionStage.TOPIC_PROPOSED, nullable=False, index=True)

    # تاریخی تحقیق و مآخذ
    historical_notes_urdu = Column(Text, nullable=True)
    verified_sources_json = Column(Text, nullable=False, default="[]")       # مستند کتب
    disputed_points_notes_urdu = Column(Text, nullable=True)                 # اختلافی مقامات

    # اسکرپٹ
    opening_hook_urdu = Column(Text, nullable=True)                          # 15 سیکنڈ ہوک
    script_outline_urdu = Column(Text, nullable=True)                        # خاکہ
    full_script_draft_urdu = Column(Text, nullable=True)                     # مکمل اسکرپٹ

    # بصری مناظر و پرامپٹس
    scene_prompts_json = Column(Text, nullable=False, default="[]")          # مناظر کے پرامپٹس

    # صداکاری و ایڈیٹنگ
    voiceover_checklist_json = Column(Text, nullable=False, default="[]")    # چیک لسٹ

    # میٹا ڈیٹا برائے یوٹیوب
    suggested_titles_json = Column(Text, nullable=False, default="[]")
    description_draft_urdu = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=False, default="[]")
    thumbnail_concept_urdu = Column(Text, nullable=True)

    target_publish_date = Column(String(20), nullable=True)                  # YYYY-MM-DD
    reviewer_notes_urdu = Column(Text, nullable=True)
    is_publication_approved = Column(Boolean, default=False)                 # صریح منظوری کا نشان

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 6 — Unified Dashboard & Approval Queue Tables (additive only)
# ---------------------------------------------------------------------------

class ApprovalState(str, enum.Enum):
    PENDING = "PENDING"                        # 1. زیر التواء (Pending Approval)
    APPROVED = "APPROVED"                      # 2. منظور شدہ (Approved)
    REJECTED = "REJECTED"                      # 3. مسترد (Rejected)
    CHANGES_REQUESTED = "CHANGES_REQUESTED"    # 4. ترمیم درکار (Changes Requested)
    EXECUTING = "EXECUTING"                    # 5. عمل جاری (Executing)
    COMPLETED = "COMPLETED"                    # 6. مکمل شدہ (Completed)
    FAILED = "FAILED"                          # 7. ناکام رہا (Failed)


class ApprovalActionType(str, enum.Enum):
    VIDEO_PUBLICATION = "VIDEO_PUBLICATION"    # ویڈیو کی اشاعت
    COMMUNITY_POST = "COMMUNITY_POST"          # کمیونٹی کوئز یا پول
    TOPIC_PROPOSAL = "TOPIC_PROPOSAL"          # نیا تاریخی موضوع
    DRAFT_REPLY = "DRAFT_REPLY"                # کمنٹ کا جواب


class ApprovalItem(Base):
    """منظوری قطار کے اندراجات (Phase 6 - Approval Queue)"""
    __tablename__ = "approval_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type = Column(Enum(ApprovalActionType), nullable=False, index=True)
    target_reference_id = Column(String(100), nullable=False)   # پروجیکٹ کوڈ یا پوسٹ آئی ڈی
    title_urdu = Column(String(500), nullable=False)
    action_details_urdu = Column(Text, nullable=False)          # صریح کارروائی کی تفصیل
    state = Column(Enum(ApprovalState), default=ApprovalState.PENDING, nullable=False, index=True)
    reviewer_note_urdu = Column(Text, nullable=True)
    actioned_by = Column(String(100), nullable=True)            # ایڈمن کا نام

    created_at = Column(DateTime, default=datetime.utcnow)
    actioned_at = Column(DateTime, nullable=True)




