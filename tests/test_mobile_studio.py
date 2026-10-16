"""
test_mobile_studio.py — Mobile Studio & Instant Publish API Tests
=================================================================
ٹیسٹ کرتا ہے:
1. موبائل UI کا کامیابی سے لوڈ ہونا (GET /mobile)
2. موضوع کی ڈیمانڈ پر کوئز یا پول کی فوری تخلیق (Mocking Playwright execution)
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from main import app
from agent_am.database.models import PostStatus

@pytest.fixture
def client():
    return TestClient(app)

def test_mobile_ui_renders(client):
    """موبائل اسٹوڈیو پیج کامیابی سے لوڈ ہوتا ہے"""
    resp = client.get("/mobile")
    assert resp.status_code == 200
    assert "Agent AM — موبائل اسٹوڈیو" in resp.text
    assert "موضوع درج کریں" in resp.text

@pytest.mark.asyncio
async def test_mobile_instant_publish_quiz(client):
    """موبائل سے کوئز ڈیمانڈ کی خودکار پروسیسنگ"""
    mock_pub = {
        "success": True,
        "status": PostStatus.PUBLISHED,
        "external_id": "yt_test_instant_123",
        "note_urdu": "ٹیسٹ کامیاب"
    }

    with patch(
        "agent_am.services.community_post_service.community_post_service.schedule_community_post",
        new=AsyncMock(return_value=mock_pub)
    ):
        resp = client.post(
            "/api/mobile/instant-publish",
            json={"topic": "احد", "post_type": "QUIZ"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "احد" in data["question"] or len(data["options"]) == 4
        assert data["external_id"] == "yt_test_instant_123"

@pytest.mark.asyncio
async def test_mobile_instant_publish_poll(client):
    """موبائل سے پول ڈیمانڈ کی خودکار پروسیسنگ"""
    mock_pub = {
        "success": True,
        "status": PostStatus.PUBLISHED,
        "external_id": "yt_test_instant_456",
        "note_urdu": "ٹیسٹ کامیاب"
    }

    with patch(
        "agent_am.services.community_post_service.community_post_service.schedule_community_post",
        new=AsyncMock(return_value=mock_pub)
    ):
        resp = client.post(
            "/api/mobile/instant-publish",
            json={"topic": "خلافت", "post_type": "POLL"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["options"]) >= 2
        assert data["external_id"] == "yt_test_instant_456"
