"""
api_router.py — Phase 6: Unified FastAPI Router for Agent AM Growth
===================================================================
The Bayaan چینل کے تمام نئے ماڈیولز کو FastAPI کے ساتھ جوڑتا ہے:
- System Overview
- Channel Analytics
- Content Recommendations & 30-Day Calendar
- Audience Insights & Draft Replies
- Video Production Pipeline (10 stages)
- Scheduled Posts (Quizzes & Polls)
- Approval Queue (7 states)
- Reports & Logs
- System Health & On-Demand Backups
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

import pytz
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent_am.config.settings import settings
from agent_am_growth.reliability.health_checker import health_checker
from agent_am_growth.reliability.backup_manager import backup_manager
from agent_am_growth.analytics.growth_comparator import growth_comparator
from agent_am_growth.analytics.metrics_collector import metrics_collector
from agent_am_growth.content_intelligence.calendar_generator import calendar_generator
from agent_am_growth.content_intelligence.topic_generator import topic_generator
from agent_am_growth.audience_manager.comment_fetcher import comment_fetcher
from agent_am_growth.audience_manager.engagement_analyzer import engagement_analyzer
from agent_am_growth.production_pipeline.pipeline_manager import pipeline_manager
from agent_am_growth.production_pipeline.script_builder import script_builder
from agent_am_growth.approvals.approval_engine import (
    approval_engine,
    ApprovalState,
    ApprovalActionType,
)
from agent_am.core.queue_manager import queue_manager

router = APIRouter(prefix="/growth", tags=["Agent AM Growth System"])
PKT = pytz.timezone("Asia/Karachi")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "agent_am" / "ui" / "templates"))



# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class ApprovalTransitionRequest(BaseModel):
    item_id: int
    target_state: ApprovalState
    reviewer_note: Optional[str] = None
    actioned_by: Optional[str] = "Admin"


class NewApprovalRequest(BaseModel):
    item_type: ApprovalActionType
    target_reference_id: str
    title_urdu: str
    action_details_urdu: str


# ---------------------------------------------------------------------------
# 1. System Overview
# ---------------------------------------------------------------------------

@router.get("/overview")
async def get_system_overview() -> Dict[str, Any]:
    """سسٹم کا مجموعی جائزہ اور لائیو صورتحال"""
    now_pkt = datetime.now(PKT)
    health = await health_checker.check_full_health()
    analytics_sum = await growth_comparator.quick_summary()
    pending_approvals = await approval_engine.list_items(state=ApprovalState.PENDING)
    upcoming_posts = await queue_manager.get_upcoming_queue(days_ahead=2)

    return {
        "channel": {
            "name": settings.CHANNEL_NAME,
            "id": settings.CHANNEL_ID,
            "timezone": settings.TIMEZONE,
            "current_time_pkt": now_pkt.strftime("%Y-%m-%d %I:%M:%S %p"),
        },
        "system_health": {
            "overall_status": health.get("overall_status", "UNKNOWN"),
            "is_healthy": health.get("overall_status") == "HEALTHY",
            "missed_tasks_count": len(health.get("missed_tasks", [])),
        },
        "analytics_summary": analytics_sum,
        "pending_approvals_count": len(pending_approvals),
        "scheduled_posts_count": len(upcoming_posts),
        "post_timings": {
            "quiz_time": "18:15 PKT (±15 منٹ رینڈم تغیر)",
            "poll_time": "20:15 PKT (±15 منٹ رینڈم تغیر)",
        }
    }


@router.get("/portal", response_class=HTMLResponse)
async def get_growth_portal(request: Request):
    """یوٹیوب گروتھ و کونٹینٹ مینجمنٹ پورٹل (Visual HTML Interface)"""
    overview_data = await get_system_overview()
    cal_data = await get_content_calendar()
    approval_items = await approval_engine.list_items()

    calendar_entries = [
        {
            "day_number": e["day_number"],
            "scheduled_date": e["target_date"],
            "category": e["category"],
            "video_title_urdu": e["video_title"],
            "opening_hook_urdu": e["notes"] or "15 سیکنڈ افتتاحی ہک اور تاریخی پس منظر",
            "community_post_proposal": f"کوئز: {e['quiz_proposal'][:40]}... / پول: {e['poll_proposal'][:40]}...",
        }
        for e in cal_data["entries"]
    ]

    approvals_formatted = [
        {
            "id": it.id,
            "item_type": it.item_type.value,
            "target_reference_id": it.target_reference_id,
            "title_urdu": it.title_urdu,
            "action_details": it.action_details_urdu,
            "state": it.state.value,
            "reviewer_note": it.reviewer_note_urdu,
            "actioned_by": it.actioned_by,
        }
        for it in approval_items
    ]

    return templates.TemplateResponse(
        request=request,
        name="growth_portal.html",
        context={
            "channel_name": settings.CHANNEL_NAME,
            "timezone": settings.TIMEZONE,
            "analytics": overview_data.get("analytics_summary", {}),
            "calendar_entries": calendar_entries,
            "approvals": approvals_formatted,
        }
    )



# ---------------------------------------------------------------------------

# 2. Channel Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics")
async def get_channel_analytics(period_days: int = Query(7, enum=[1, 7, 30, 90])) -> Dict[str, Any]:
    """یوٹیوب ترقی کا تقابلی جائزہ (1، 7، 30، 90 دن)"""
    comp = await growth_comparator.compare_periods(period_days)
    return {
        "period_days": comp.period_days,
        "period_label": comp.period_label,
        "data_points_available": comp.data_points_available,
        "has_sufficient_data": comp.has_sufficient_data,
        "insufficient_data_reason": comp.insufficient_data_reason,
        "subscribers": {
            "end_value": comp.subscriber_delta.end_value if comp.subscriber_delta else None,
            "delta": comp.subscriber_delta.delta if comp.subscriber_delta else None,
            "growth_pct": comp.subscriber_delta.growth_pct if comp.subscriber_delta else None,
        },
        "views": {
            "end_value": comp.view_delta.end_value if comp.view_delta else None,
            "delta": comp.view_delta.delta if comp.view_delta else None,
            "growth_pct": comp.view_delta.growth_pct if comp.view_delta else None,
        },
        "videos_count": comp.video_count_delta.end_value if comp.video_count_delta else None,
        "analytics_api_disclosure": comp.analytics_api_note,
    }


# ---------------------------------------------------------------------------
# 3. Content Recommendations & 30-Day Calendar
# ---------------------------------------------------------------------------

@router.get("/content-calendar")
async def get_content_calendar() -> Dict[str, Any]:
    """30 روزہ جامع اسلامی تاریخ کونٹینٹ کیلنڈر"""
    entries = await calendar_generator.get_calendar_entries()
    if not entries:
        await calendar_generator.generate_and_save_calendar()
        entries = await calendar_generator.get_calendar_entries()

    proposals = await topic_generator.get_all_proposals()

    return {
        "total_days": len(entries),
        "entries": [
            {
                "day_number": e.day_number,
                "target_date": e.target_date,
                "category": e.category.value,
                "video_title": e.video_title_urdu,
                "quiz_proposal": e.quiz_proposal_urdu,
                "poll_proposal": e.poll_proposal_urdu,
                "priority": e.production_priority,
                "notes": e.notes_urdu,
            }
            for e in entries
        ],
        "curated_proposals_count": len(proposals),
    }


# ---------------------------------------------------------------------------
# 4. Audience Insights
# ---------------------------------------------------------------------------

@router.get("/audience")
async def get_audience_insights() -> Dict[str, Any]:
    """سامعین کے تبصروں کا تجزیہ اور ڈرافٹ جوابات"""
    summary = await engagement_analyzer.analyze_and_update_comments()
    comments = await comment_fetcher.get_stored_comments(limit=20)

    return {
        "total_comments": summary.total_comments,
        "positive_count": summary.positive_count,
        "question_count": summary.question_count,
        "request_count": summary.request_count,
        "confusion_count": summary.confusion_count,
        "frequent_questions": summary.frequent_questions,
        "topic_requests": summary.topic_requests,
        "proposed_quiz_poll_topics": summary.proposed_quiz_poll_topics,
        "recent_comments": [
            {
                "author": c.author_name,
                "text": c.text_original,
                "sentiment": c.sentiment.value,
                "draft_reply": c.draft_reply_urdu,
                "draft_status": c.draft_status.value,
            }
            for c in comments
        ],
        "safety_guarantee": "تمام جوابات صرف مسودہ (Drafts Only) ہیں۔ سسٹم خودکار پوسٹنگ نہیں کرتا۔",
    }


# ---------------------------------------------------------------------------
# 5. Video Production Pipeline
# ---------------------------------------------------------------------------

@router.get("/production")
async def get_production_pipeline() -> Dict[str, Any]:
    """ویڈیو پروڈکشن پائپ لائن کے پروجیکٹس اور 10 مراحل کا ٹریکر"""
    # فلیگ شپ پروجیکٹ سیڈ کریں اگر موجود نہ ہو
    await script_builder.seed_flagship_project()
    projects = await pipeline_manager.list_all_projects()

    return {
        "total_projects": len(projects),
        "projects": [
            {
                "project_code": p.project_code,
                "title_urdu": p.title_urdu,
                "stage": p.stage.value,
                "target_publish_date": p.target_publish_date,
                "is_publication_approved": p.is_publication_approved,
                "reviewer_notes": p.reviewer_notes_urdu,
            }
            for p in projects
        ]
    }


@router.get("/production/{project_code}")
async def get_production_project_detail(project_code: str) -> Dict[str, Any]:
    """ایک پروجیکٹ کا مکمل پروڈکشن اسکرپٹ اور بصری پرامپٹس"""
    p = await pipeline_manager.get_project(project_code)
    if not p:
        raise HTTPException(status_code=404, detail="پروجیکٹ نہیں ملا")

    import json
    return {
        "project_code": p.project_code,
        "title_urdu": p.title_urdu,
        "stage": p.stage.value,
        "historical_notes": p.historical_notes_urdu,
        "verified_sources": json.loads(p.verified_sources_json or "[]"),
        "disputed_points": p.disputed_points_notes_urdu,
        "opening_hook": p.opening_hook_urdu,
        "script_outline": p.script_outline_urdu,
        "full_script_draft": p.full_script_draft_urdu,
        "scene_prompts": json.loads(p.scene_prompts_json or "[]"),
        "voiceover_checklist": json.loads(p.voiceover_checklist_json or "[]"),
        "titles": json.loads(p.suggested_titles_json or "[]"),
        "description": p.description_draft_urdu,
        "tags": json.loads(p.tags_json or "[]"),
        "thumbnail_concept": p.thumbnail_concept_urdu,
        "is_publication_approved": p.is_publication_approved,
    }


# ---------------------------------------------------------------------------
# 6. Approval Queue
# ---------------------------------------------------------------------------

@router.get("/approvals")
async def list_approvals(state: Optional[ApprovalState] = None) -> Dict[str, Any]:
    """منظوری کی قطار اور تاریخچہ"""
    items = await approval_engine.list_items(state=state)
    return {
        "total_items": len(items),
        "items": [
            {
                "id": it.id,
                "item_type": it.item_type.value,
                "target_reference_id": it.target_reference_id,
                "title_urdu": it.title_urdu,
                "action_details": it.action_details_urdu,
                "state": it.state.value,
                "reviewer_note": it.reviewer_note_urdu,
                "actioned_by": it.actioned_by,
                "created_at": it.created_at.isoformat() if it.created_at else None,
                "actioned_at": it.actioned_at.isoformat() if it.actioned_at else None,
            }
            for it in items
        ]
    }


@router.post("/approvals/transition")
async def transition_approval(req: ApprovalTransitionRequest) -> Dict[str, Any]:
    """منظوری کی حالت تبدیل کرے (Approved, Rejected, Changes Requested)"""
    res = await approval_engine.transition_state(
        item_id=req.item_id,
        target_state=req.target_state,
        reviewer_note=req.reviewer_note,
        actioned_by=req.actioned_by or "Admin",
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.post("/approvals/submit")
async def submit_approval(req: NewApprovalRequest) -> Dict[str, Any]:
    """نئی منظوری کی درخواست جمع کروائے"""
    item = await approval_engine.submit_for_approval(
        item_type=req.item_type,
        target_reference_id=req.target_reference_id,
        title_urdu=req.title_urdu,
        action_details_urdu=req.action_details_urdu,
    )
    return {"success": True, "item_id": item.id, "state": item.state.value}


# ---------------------------------------------------------------------------
# 7. Reports & Logs
# ---------------------------------------------------------------------------

@router.get("/reports")
async def list_reports() -> Dict[str, Any]:
    """تمام تیار شدہ مارک ڈاؤن اور ایچ ٹی ایم ایل رپورٹس کی فہرست"""
    reports_dir = settings.REPORTS_DIR
    if not os.path.exists(reports_dir):
        return {"reports": []}

    files = []
    for fname in os.listdir(reports_dir):
        fpath = os.path.join(reports_dir, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            files.append({
                "filename": fname,
                "size_kb": round(stat.st_size / 1024, 1),
                "created_at": datetime.fromtimestamp(stat.st_ctime, PKT).strftime("%Y-%m-%d %I:%M %p"),
                "url": f"/reports/{fname}",
            })

    # تاریخ کے اعتبار سے ترتیب
    files.sort(key=lambda x: x["filename"], reverse=True)
    return {"reports": files}


# ---------------------------------------------------------------------------
# 8. System Health & Backups
# ---------------------------------------------------------------------------

@router.get("/health-check")
async def get_system_health() -> Dict[str, Any]:
    """سسٹم کے تمام اجزاء کی مفصل ہیلتھ جانچ"""
    res = await health_checker.check_full_health()
    return res



@router.post("/backup/trigger")
async def trigger_backup() -> Dict[str, Any]:
    """فوری آن ڈیمانڈ SQLite ڈیٹا بیس بیک اپ تیار کرے"""
    res = backup_manager.create_backup(label="dashboard_ondemand")
    return res


@router.get("/backups")
async def list_backups() -> Dict[str, Any]:
    """موجودہ تمام ڈیٹا بیس بیک اپس کی فہرست"""
    backups = backup_manager.list_backups()
    return {"total_backups": len(backups), "backups": backups}
