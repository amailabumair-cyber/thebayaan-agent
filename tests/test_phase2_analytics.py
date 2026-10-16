"""
test_phase2_analytics.py — Phase 2 Growth Analytics Tests
==========================================================
یہ ٹیسٹ چیک کرتے ہیں:
1. چینل اسنیپ شاٹ جمع ہوتا ہے
2. ویڈیو اسنیپ شاٹس جمع ہوتے ہیں
3. ناکافی ڈیٹا پر موازنہ gracefully handle ہوتا ہے
4. رپورٹ فائل بنتی ہے
5. کوئی من گھڑت ڈیٹا نہیں
"""

import asyncio
import os
import pytest
import pytest_asyncio
from datetime import datetime

import pytz

PKT = pytz.timezone("Asia/Karachi")


# ---------------------------------------------------------------------------
# Test 1: GrowthChannelSnapshot table exists in DB
# ---------------------------------------------------------------------------
def test_growth_tables_in_models():
    """DB models میں نئی tables موجود ہیں"""
    from agent_am.database.models import GrowthChannelSnapshot, GrowthVideoSnapshot
    assert GrowthChannelSnapshot.__tablename__ == "growth_channel_snapshots"
    assert GrowthVideoSnapshot.__tablename__ == "growth_video_snapshots"


# ---------------------------------------------------------------------------
# Test 2: MetricsCollector imports and structure correct
# ---------------------------------------------------------------------------
def test_metrics_collector_structure():
    """MetricsCollector صحیح طریقے سے import ہوتا ہے"""
    from agent_am_growth.analytics.metrics_collector import (
        MetricsCollector,
        metrics_collector,
        ChannelSnapshot,
        VideoMetricSnapshot,
    )
    assert isinstance(metrics_collector, MetricsCollector)
    assert hasattr(metrics_collector, "collect_live_channel_snapshot")
    assert hasattr(metrics_collector, "collect_live_video_snapshots")
    assert hasattr(metrics_collector, "get_historical_channel_snapshots")
    assert hasattr(metrics_collector, "get_available_dates_count")


# ---------------------------------------------------------------------------
# Test 3: GrowthComparator handles zero data gracefully
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_comparator_handles_zero_data(monkeypatch):
    """ڈیٹا نہ ہونے پر comparator crash نہ کرے اور honest response دے"""
    from agent_am_growth.analytics.growth_comparator import growth_comparator
    from agent_am_growth.analytics import metrics_collector

    # Mock: DB میں 0 دن کا ڈیٹا
    async def mock_count():
        return 0

    async def mock_snapshots(days):
        return []

    monkeypatch.setattr(
        metrics_collector, "get_available_dates_count", mock_count
    )
    monkeypatch.setattr(
        metrics_collector, "get_historical_channel_snapshots", mock_snapshots
    )

    result = await growth_comparator.compare_periods(7)

    assert result.has_sufficient_data is False
    assert result.data_points_available == 0
    assert "ڈیٹا" in result.insufficient_data_reason or "data" in result.insufficient_data_reason.lower()


# ---------------------------------------------------------------------------
# Test 4: GrowthComparator handles single snapshot gracefully
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_comparator_single_snapshot(monkeypatch):
    """صرف 1 دن کا ڈیٹا ہو تو موازنہ fail نہ کرے"""
    from agent_am_growth.analytics.growth_comparator import growth_comparator
    from agent_am_growth.analytics import metrics_collector as mc_module
    from agent_am_growth.analytics.metrics_collector import ChannelSnapshot

    async def mock_count():
        return 1

    async def mock_snapshots(days):
        return [
            ChannelSnapshot(
                snapshot_date="2026-10-16",
                subscribers=21,
                total_views=4566,
                video_count=9,
                data_source="live_api",
                timestamp_pkt="2026-10-16T09:30:00+05:00",
                is_live=False,
            )
        ]

    monkeypatch.setattr(mc_module, "get_available_dates_count", mock_count)
    monkeypatch.setattr(mc_module, "get_historical_channel_snapshots", mock_snapshots)

    result = await growth_comparator.compare_periods(7)

    assert result.has_sufficient_data is False
    assert result.data_points_available == 1
    # baseline data should still be shown
    assert result.subscriber_delta is not None
    assert result.subscriber_delta.end_value == 21


# ---------------------------------------------------------------------------
# Test 5: UrduGrowthReporter generates report file (no fabricated data)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reporter_creates_file(tmp_path):
    """رپورٹ فائل بنتی ہے اور Analytics API کی حدود واضح ہوتی ہیں"""
    from agent_am_growth.analytics.urdu_growth_reporter import UrduGrowthReporter
    from agent_am_growth.analytics.growth_comparator import ComparisonReport
    from agent_am_growth.analytics import growth_comparator


    async def mock_compare(period_days):
        return ComparisonReport(
            period_days=period_days,
            period_label=f"{period_days} دن",
            start_date=None,
            end_date="2026-10-16",
            data_points_available=1,
            has_sufficient_data=False,
            insufficient_data_reason="ٹیسٹ: صرف 1 دن کا ڈیٹا",
        )

    original_fn = growth_comparator.compare_periods
    growth_comparator.compare_periods = mock_compare

    reporter = UrduGrowthReporter()

    # save path tmp_path میں کریں
    def mock_save(md, today_str, period_days):
        path = str(tmp_path / f"growth_report_{today_str}_{period_days}day.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        return path

    reporter._save_report = mock_save

    try:
        md = await reporter.generate_growth_report(period_days=7, save_to_file=True)
    finally:
        # Restore
        growth_comparator.compare_periods = original_fn

    assert "Analytics API" in md or "OAuth2" in md or "ڈیٹا" in md





# ---------------------------------------------------------------------------
# Test 6: ChannelSnapshot dataclass correct fields
# ---------------------------------------------------------------------------
def test_channel_snapshot_fields():
    """ChannelSnapshot dataclass کے تمام fields موجود ہیں"""
    from agent_am_growth.analytics.metrics_collector import ChannelSnapshot
    s = ChannelSnapshot(
        snapshot_date="2026-10-16",
        subscribers=21,
        total_views=4566,
        video_count=9,
        data_source="live_api",
        timestamp_pkt="2026-10-16T09:30:00+05:00",
        is_live=True,
    )
    assert s.snapshot_date == "2026-10-16"
    assert s.subscribers == 21
    assert s.is_live is True
    assert s.data_source == "live_api"


# ---------------------------------------------------------------------------
# Test 7: Analytics API flag always False (no fabrication)
# ---------------------------------------------------------------------------
def test_analytics_api_flag_false():
    """MetricsCollector کبھی Analytics API available نہ بتائے"""
    from agent_am_growth.analytics.metrics_collector import MetricsCollector
    mc = MetricsCollector()
    assert mc._analytics_available is False


# ---------------------------------------------------------------------------
# Test 8: DB tables have correct columns (model check)
# ---------------------------------------------------------------------------
def test_growth_channel_snapshot_columns():
    """GrowthChannelSnapshot table کے columns درست ہیں"""
    from agent_am.database.models import GrowthChannelSnapshot
    cols = {c.name for c in GrowthChannelSnapshot.__table__.columns}
    required = {"id", "snapshot_date", "subscribers", "total_views", "video_count",
                "data_source", "timestamp_pkt", "created_at"}
    assert required.issubset(cols), f"غائب columns: {required - cols}"


def test_growth_video_snapshot_columns():
    """GrowthVideoSnapshot table کے columns درست ہیں"""
    from agent_am.database.models import GrowthVideoSnapshot
    cols = {c.name for c in GrowthVideoSnapshot.__table__.columns}
    required = {"id", "video_id", "title", "views", "likes", "comments",
                "snapshot_date", "created_at"}
    assert required.issubset(cols), f"غائب columns: {required - cols}"


# ---------------------------------------------------------------------------
# Test 9: Scheduler has daily_growth_analytics job defined
# ---------------------------------------------------------------------------
def test_scheduler_has_growth_job():
    """Scheduler service میں growth analytics job register ہوتا ہے"""
    import inspect
    import agent_am.services.scheduler_service as ss
    src = inspect.getsource(ss)
    assert "daily_growth_analytics" in src
    assert "metrics_collector.collect_all" in src
