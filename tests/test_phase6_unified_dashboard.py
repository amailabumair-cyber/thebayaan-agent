"""
test_phase6_unified_dashboard.py — Phase 6 Unified Dashboard & Approval Queue Tests
==================================================================================
یہ ٹیسٹس چیک کرتے ہیں:
1. منظوری کی 7 ریاستوں پر مشتمل اسٹیٹ مشین (Approval State Machine)
2. صریح اور محفوظ اجازت کا نظام (Targeted Authorization)
3. فاسٹ اے پی آئی (FastAPI) کے تمام توسیعی اینڈپوائنٹس
4. پچھلے مرکزی روٹس (مبنی بر index.html اور موجودہ API) کا بلا تعطل کام کرنا
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from agent_am.database.models import (
    ApprovalState,
    ApprovalActionType,
    ApprovalItem,
)
from agent_am_growth.approvals.approval_engine import (
    approval_engine,
    VALID_TRANSITIONS,
)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: Approval States & Transitions
# ---------------------------------------------------------------------------
def test_approval_states_and_transitions():
    """تمام 7 ریاستیں اور جائز ٹرانزیشنز موجود ہیں"""
    assert len(ApprovalState) == 7
    assert ApprovalState.PENDING in VALID_TRANSITIONS
    assert ApprovalState.APPROVED in VALID_TRANSITIONS
    assert ApprovalState.REJECTED in VALID_TRANSITIONS
    assert ApprovalState.CHANGES_REQUESTED in VALID_TRANSITIONS
    assert ApprovalState.EXECUTING in VALID_TRANSITIONS
    assert ApprovalState.COMPLETED in VALID_TRANSITIONS
    assert ApprovalState.FAILED in VALID_TRANSITIONS


@pytest.mark.asyncio
async def test_approval_engine_lifecycle():
    """آئٹم جمع کرنے اور اسٹیٹ ٹرانزیشن کا مکمل ٹیسٹ"""
    # 1. نئی درخواست
    item = await approval_engine.submit_for_approval(
        item_type=ApprovalActionType.COMMUNITY_POST,
        target_reference_id="POST-TEST-001",
        title_urdu="ٹیسٹ کمیونٹی کوئز",
        action_details_urdu="شام 6:15 بجے یوٹیوب پر اشاعت",
    )
    assert item.state == ApprovalState.PENDING

    # 2. ترمیم درکار (Changes Requested)
    ch_res = await approval_engine.transition_state(
        item_id=item.id,
        target_state=ApprovalState.CHANGES_REQUESTED,
        reviewer_note="سوال کا چوتھا آپشن تبدیل کریں",
    )
    assert ch_res["success"] is True
    assert ch_res["new_state"] == "CHANGES_REQUESTED"

    # 3. دوبارہ پینڈنگ
    p_res = await approval_engine.transition_state(
        item_id=item.id,
        target_state=ApprovalState.PENDING,
        reviewer_note="آپشن درست کر دیا گیا",
    )
    assert p_res["success"] is True

    # 4. منظوری (Approved)
    app_res = await approval_engine.transition_state(
        item_id=item.id,
        target_state=ApprovalState.APPROVED,
        reviewer_note="منظور کیا جاتا ہے",
    )
    assert app_res["success"] is True
    assert app_res["new_state"] == "APPROVED"


@pytest.mark.asyncio
async def test_invalid_transition_rejected():
    """غیر قانونی اسٹیٹ جمپ کی ممانعت"""
    item = await approval_engine.submit_for_approval(
        item_type=ApprovalActionType.TOPIC_PROPOSAL,
        target_reference_id="TOPIC-TEST-002",
        title_urdu="ٹیسٹ غیر قانونی ٹرانزیشن",
        action_details_urdu="ٹیسٹ",
    )
    # PENDING سے سیدھا COMPLETED کی کوشش
    fail_res = await approval_engine.transition_state(
        item_id=item.id,
        target_state=ApprovalState.COMPLETED,
    )
    assert fail_res["success"] is False
    assert "تبدیلی کی اجازت نہیں" in fail_res["error"]


# ---------------------------------------------------------------------------
# Test 2: FastAPI Growth Endpoints
# ---------------------------------------------------------------------------
def test_api_growth_overview(client):
    """مرکزی توسیعی جائزہ اینڈپوائنٹ 200 OK دیتا ہے"""
    resp = client.get("/growth/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "channel" in data
    assert "system_health" in data
    assert "post_timings" in data
    assert "18:15" in data["post_timings"]["quiz_time"]


def test_api_growth_analytics(client):
    """اینالیٹکس اینڈپوائنٹ ڈیٹا کی شفافیت کے ساتھ واپس آتا ہے"""
    resp = client.get("/growth/analytics?period_days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_days"] == 7
    assert "analytics_api_disclosure" in data
    assert "subscribers" in data


def test_api_growth_content_calendar(client):
    """30 روزہ کیلنڈر اینڈپوائنٹ 200 OK دیتا ہے"""
    resp = client.get("/growth/content-calendar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_days"] == 30
    assert len(data["entries"]) == 30


def test_api_growth_audience(client):
    """سامعین کے تاثرات کا اینڈپوائنٹ 200 OK اور ڈرافٹ سیفٹی دیتا ہے"""
    resp = client.get("/growth/audience")
    assert resp.status_code == 200
    data = resp.json()
    assert "safety_guarantee" in data
    assert "Drafts Only" in data["safety_guarantee"]


def test_api_growth_production(client):
    """پروڈکشن پائپ لائن اینڈپوائنٹ پروجیکٹس واپس کرتا ہے"""
    resp = client.get("/growth/production")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_projects"] >= 1


def test_api_growth_approvals_list(client):
    """منظوری قطار لسٹ اینڈپوائنٹ"""
    resp = client.get("/growth/approvals")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_api_growth_health_check(client):
    """سسٹم ہیلتھ چیک اینڈپوائنٹ"""
    resp = client.get("/growth/health-check")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert "components" in data


def test_api_growth_reports_list(client):
    """رپورٹس لسٹ اینڈپوائنٹ"""
    resp = client.get("/growth/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data
    assert len(data["reports"]) >= 1


def test_original_dashboard_remains_intact(client):
    """اصلی ڈیش بورڈ روٹ (/) بغیر کسی خرابی کے کام کرتا ہے"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "The Bayan" in resp.text or "Agent AM" in resp.text
