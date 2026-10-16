"""
metrics_collector.py — Phase 2: YouTube Growth Analytics
=========================================================
یوٹیوب چینل 'The Bayaan' کا لائیو ڈیٹا جمع کرنے اور
تاریخی اسنیپ شاٹس محفوظ کرنے کا نظام۔

اہم اصول:
- لائیو API ڈیٹا اور DB سے پرانا ڈیٹا کبھی خاموشی سے نہ ملائیں
- اگر ڈیٹا دستیاب نہ ہو تو صاف صاف بتائیں
- Analytics API (watch time, CTR) کے لیے OAuth2 درکار ہے — ابھی دستیاب نہیں
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import json

import pytz
from sqlalchemy import select, desc, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from agent_am.database.connection import AsyncSessionLocal, engine
from agent_am.database.models import (
    GrowthChannelSnapshot,
    GrowthVideoSnapshot,
    ChannelConfig,
    VideoSnapshot,
)
from agent_am.services.youtube_service import youtube_service

logger = logging.getLogger("agent_am.analytics.metrics_collector")

PKT = pytz.timezone("Asia/Karachi")



# ---------------------------------------------------------------------------
# Data Classes (typed containers — no business logic)
# ---------------------------------------------------------------------------

@dataclass
class ChannelSnapshot:
    """چینل کی کارکردگی کا ایک مکمل اسنیپ شاٹ"""
    snapshot_date: str           # YYYY-MM-DD (PKT)
    subscribers: int
    total_views: int
    video_count: int
    data_source: str             # "live_api" یا "snapshot_db"
    timestamp_pkt: str           # ISO 8601 با PKT timezone
    is_live: bool = True         # لائیو API سے آیا = True، پرانے DB سے = False


@dataclass
class VideoMetricSnapshot:
    """ایک ویڈیو کی کارکردگی کا مکمل اسنیپ شاٹ"""
    video_id: str
    title: str
    views: int
    likes: int
    comments: int
    snapshot_date: str           # YYYY-MM-DD (PKT)
    duration_seconds: int = 0
    published_at: Optional[datetime] = None
    is_live: bool = True         # لائیو API سے آیا = True


@dataclass
class CollectionResult:
    """ڈیٹا اکٹھا کرنے کے نتیجے کی مکمل رپورٹ"""
    success: bool
    channel_snapshot: Optional[ChannelSnapshot] = None
    video_snapshots: List[VideoMetricSnapshot] = field(default_factory=list)
    videos_saved: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    analytics_api_available: bool = False  # OAuth2 ابھی configure نہیں


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

class MetricsCollector:
    """
    YouTube Data API v3 سے لائیو ڈیٹا جمع کرتا ہے اور DB میں محفوظ کرتا ہے۔

    حدود (جو کبھی نہ چھپائی جائیں):
    - YouTube Analytics API (watch time, CTR, impressions): OAuth2 token درکار ہے
      جو ابھی configure نہیں — یہ میٹرکس رپورٹ میں 'دستیاب نہیں' لکھیں گے
    - صرف وہی ڈیٹا دکھائیں جو API سے واقعی ملا ہو
    """

    def __init__(self):
        self._analytics_available = False  # OAuth2 کنفیگر نہیں ہے

    # ------------------------------------------------------------------
    # لائیو چینل اسنیپ شاٹ
    # ------------------------------------------------------------------

    async def collect_live_channel_snapshot(self) -> CollectionResult:
        """
        YouTube Data API سے چینل کا لائیو ڈیٹا لے کر DB میں محفوظ کرے۔
        اگر آج کا ریکارڈ پہلے سے موجود ہو تو دوبارہ نہ بنائے (idempotent)۔
        """
        now_pkt = datetime.now(PKT)
        today_str = now_pkt.strftime("%Y-%m-%d")
        timestamp_pkt = now_pkt.isoformat()

        result = CollectionResult(success=False, analytics_api_available=False)

        try:
            # لائیو API کال
            logger.info(f"چینل ڈیٹا لائیو API سے لے رہے ہیں: {today_str}")
            channel_data = await youtube_service.get_channel_details()

            if not channel_data:
                result.errors.append("YouTube API نے چینل ڈیٹا واپس نہیں کیا")
                logger.error("YouTube API سے خالی جواب ملا")
                return result

            # ڈیٹا نکالیں
            subs = int(channel_data.get("subscribers", 0))
            views = int(channel_data.get("views", 0))
            vids = int(channel_data.get("video_count", 0))

            snapshot = ChannelSnapshot(
                snapshot_date=today_str,
                subscribers=subs,
                total_views=views,
                video_count=vids,
                data_source="live_api",
                timestamp_pkt=timestamp_pkt,
                is_live=True,
            )

            # DB میں محفوظ کریں (duplicate ignore)
            async with AsyncSessionLocal() as session:
                stmt = sqlite_insert(GrowthChannelSnapshot).values(
                    snapshot_date=today_str,
                    subscribers=subs,
                    total_views=views,
                    video_count=vids,
                    data_source="live_api",
                    timestamp_pkt=timestamp_pkt,
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=["snapshot_date"])
                await session.execute(stmt)
                await session.commit()

            result.success = True
            result.channel_snapshot = snapshot
            result.warnings.append(
                "Analytics API (watch time, CTR, impressions) دستیاب نہیں — OAuth2 token درکار ہے"
            )
            logger.info(f"چینل اسنیپ شاٹ محفوظ: subscribers={subs}, views={views}, videos={vids}")

        except Exception as e:
            msg = f"چینل اسنیپ شاٹ خرابی: {e}"
            result.errors.append(msg)
            logger.exception(msg)

        return result

    # ------------------------------------------------------------------
    # لائیو ویڈیو اسنیپ شاٹس
    # ------------------------------------------------------------------

    async def collect_live_video_snapshots(self) -> CollectionResult:
        """
        تمام حالیہ ویڈیوز کا لائیو ڈیٹا YouTube API سے لے کر DB میں محفوظ کرے۔
        """
        now_pkt = datetime.now(PKT)
        today_str = now_pkt.strftime("%Y-%m-%d")
        result = CollectionResult(success=False, analytics_api_available=False)

        try:
            logger.info(f"ویڈیو اسنیپ شاٹس لائیو API سے لے رہے ہیں: {today_str}")
            videos_data = await youtube_service.get_recent_videos()

            if not videos_data:
                result.errors.append("YouTube API نے ویڈیوز واپس نہیں کیے")
                return result

            video_snapshots = []
            saved_count = 0

            async with AsyncSessionLocal() as session:
                for vd in videos_data:
                    vid_id = vd.get("video_id") or vd.get("id", "")
                    if not vid_id:
                        continue

                    # published_at parse
                    pub_at = None
                    pub_str = vd.get("published_at") or vd.get("publishedAt")
                    if pub_str:
                        try:
                            pub_at = datetime.fromisoformat(
                                pub_str.replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    views = int(vd.get("view_count", 0) or vd.get("viewCount", 0) or 0)
                    likes = int(vd.get("like_count", 0) or vd.get("likeCount", 0) or 0)
                    comments = int(vd.get("comment_count", 0) or vd.get("commentCount", 0) or 0)
                    title = vd.get("title", "")[:499]

                    vs = VideoMetricSnapshot(
                        video_id=vid_id,
                        title=title,
                        views=views,
                        likes=likes,
                        comments=comments,
                        snapshot_date=today_str,
                        duration_seconds=0,
                        published_at=pub_at,
                        is_live=True,
                    )
                    video_snapshots.append(vs)

                    # DB insert (duplicate ignore via unique constraint)
                    stmt = sqlite_insert(GrowthVideoSnapshot).values(
                        video_id=vid_id,
                        title=title,
                        views=views,
                        likes=likes,
                        comments=comments,
                        snapshot_date=today_str,
                        duration_seconds=0,
                        published_at=pub_at,
                    )
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=["video_id", "snapshot_date"]
                    )
                    await session.execute(stmt)
                    saved_count += 1

                await session.commit()

            result.success = True
            result.video_snapshots = video_snapshots
            result.videos_saved = saved_count
            result.warnings.append(
                "Analytics API (watch time, CTR) دستیاب نہیں — OAuth2 token درکار ہے"
            )
            logger.info(f"{saved_count} ویڈیو اسنیپ شاٹس محفوظ ہوئے")

        except Exception as e:
            msg = f"ویڈیو اسنیپ شاٹس خرابی: {e}"
            result.errors.append(msg)
            logger.exception(msg)

        return result

    # ------------------------------------------------------------------
    # تاریخی ڈیٹا پڑھنا
    # ------------------------------------------------------------------

    async def get_historical_channel_snapshots(self, days: int = 90) -> List[ChannelSnapshot]:
        """
        DB سے پچھلے N دن کے چینل اسنیپ شاٹس واپس کرے۔
        نوٹ: لائیو اور cached ڈیٹا data_source field سے پہچانیں۔
        """
        cutoff = (datetime.now(PKT) - timedelta(days=days)).strftime("%Y-%m-%d")
        results = []

        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(GrowthChannelSnapshot)
                    .where(GrowthChannelSnapshot.snapshot_date >= cutoff)
                    .order_by(GrowthChannelSnapshot.snapshot_date.asc())
                )
                rows = await session.scalars(stmt)
                for row in rows:
                    results.append(
                        ChannelSnapshot(
                            snapshot_date=row.snapshot_date,
                            subscribers=row.subscribers,
                            total_views=row.total_views,
                            video_count=row.video_count,
                            data_source=row.data_source,
                            timestamp_pkt=row.timestamp_pkt or "",
                            is_live=False,  # DB سے آیا ہے، ابھی live نہیں
                        )
                    )
        except Exception as e:
            logger.exception(f"تاریخی چینل ڈیٹا لانے میں خرابی: {e}")

        return results

    async def get_historical_video_snapshots(
        self, days: int = 30, video_id: Optional[str] = None
    ) -> List[VideoMetricSnapshot]:
        """
        DB سے پچھلے N دن کے ویڈیو اسنیپ شاٹس واپس کرے۔
        video_id دیا ہو تو صرف وہ ویڈیو، ورنہ سب۔
        """
        cutoff = (datetime.now(PKT) - timedelta(days=days)).strftime("%Y-%m-%d")
        results = []

        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(GrowthVideoSnapshot)
                    .where(GrowthVideoSnapshot.snapshot_date >= cutoff)
                )
                if video_id:
                    stmt = stmt.where(GrowthVideoSnapshot.video_id == video_id)
                stmt = stmt.order_by(
                    GrowthVideoSnapshot.snapshot_date.asc(),
                    GrowthVideoSnapshot.views.desc(),
                )
                rows = await session.scalars(stmt)
                for row in rows:
                    results.append(
                        VideoMetricSnapshot(
                            video_id=row.video_id,
                            title=row.title,
                            views=row.views,
                            likes=row.likes,
                            comments=row.comments,
                            snapshot_date=row.snapshot_date,
                            duration_seconds=row.duration_seconds,
                            published_at=row.published_at,
                            is_live=False,
                        )
                    )
        except Exception as e:
            logger.exception(f"تاریخی ویڈیو ڈیٹا لانے میں خرابی: {e}")

        return results

    async def get_available_dates_count(self) -> int:
        """DB میں کتنے الگ الگ دنوں کا چینل ڈیٹا موجود ہے"""
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import func
                result = await session.execute(
                    select(func.count(GrowthChannelSnapshot.id))
                )
                return result.scalar() or 0
        except Exception:
            return 0

    async def collect_all(self) -> Dict[str, Any]:
        """
        چینل اور ویڈیوز — دونوں کا ڈیٹا اکٹھا کرے۔
        روزانہ 9:30 بجے scheduler سے call ہوتا ہے۔
        """
        logger.info("روزانہ Growth Analytics ڈیٹا اکٹھا کرنا شروع...")
        ch_result = await self.collect_live_channel_snapshot()
        vid_result = await self.collect_live_video_snapshots()

        summary = {
            "channel_success": ch_result.success,
            "videos_success": vid_result.success,
            "videos_saved": vid_result.videos_saved,
            "channel_errors": ch_result.errors,
            "video_errors": vid_result.errors,
            "warnings": ch_result.warnings[:1],  # Analytics API notice
            "analytics_api_available": False,
        }
        logger.info(f"Growth Analytics مکمل: {summary}")
        return summary


# Singleton
metrics_collector = MetricsCollector()
