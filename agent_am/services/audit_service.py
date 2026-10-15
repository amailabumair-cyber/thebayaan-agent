import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import VideoSnapshot, ChannelConfig
from agent_am.services.youtube_service import youtube_service
from agent_am.services.ai_engine import ai_engine

logger = logging.getLogger("agent_am.audit_service")

class AuditService:
    """
    چینل 'The Bayan' کا روزانہ آڈٹ کرنے والی سروس (Channel Audit Service)
    ویڈیوز کی کارکردگی، ویوز، لائیکس، کمنٹس اور پیش رفت کا جامع تجزیہ کرتی ہے۔
    """

    async def perform_daily_audit(self) -> Dict[str, Any]:
        """
        روزانہ کا مکمل آڈٹ رن کرتی ہے اور نتائج فراہم کرتی ہے
        """
        now_pkt = settings.now()
        report_date = now_pkt.strftime("%Y-%m-%d")
        period_start = now_pkt - timedelta(days=1)
        period_end = now_pkt

        logger.info(f"تاریخ {report_date} کے لیے چینل آڈٹ کا آغاز برائے 'The Bayan'")

        # 1. یوٹیوب سے تازہ تفصیلات لائیں
        channel_data = await youtube_service.get_channel_details()
        recent_videos = await youtube_service.get_recent_videos(max_results=15)

        # 2. ڈیٹا بیس میں ویڈیو اسنیپ شاٹس محفوظ کریں
        async with AsyncSessionLocal() as session:
            for v in recent_videos:
                snapshot = VideoSnapshot(
                    video_id=v["video_id"],
                    title=v["title"],
                    published_at=datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")) if v["published_at"] else None,
                    view_count=v["views"],
                    like_count=v["likes"],
                    comment_count=v["comments"],
                    snapshot_date=report_date
                )
                session.add(snapshot)

            # چینل کنفیگ اپڈیٹ
            stmt = select(ChannelConfig).where(ChannelConfig.channel_name == settings.CHANNEL_NAME)
            res = await session.execute(stmt)
            ch_cfg = res.scalar_one_or_none()
            if not ch_cfg:
                ch_cfg = ChannelConfig(
                    channel_name=settings.CHANNEL_NAME,
                    channel_id=channel_data.get("channel_id"),
                    custom_url=channel_data.get("custom_url"),
                    total_subscribers=channel_data.get("subscribers", 0),
                    total_views=channel_data.get("views", 0),
                    total_videos=channel_data.get("video_count", 0),
                    last_verified_at=now_pkt
                )
                session.add(ch_cfg)
            else:
                ch_cfg.total_subscribers = channel_data.get("subscribers", 0)
                ch_cfg.total_views = channel_data.get("views", 0)
                ch_cfg.total_videos = channel_data.get("video_count", 0)
                ch_cfg.last_verified_at = now_pkt

            await session.commit()

        # 3. بہترین اور بہتری طلب ویڈیوز کا تعین (Top & Underperforming)
        sorted_videos = sorted(recent_videos, key=lambda x: x.get("views", 0), reverse=True)
        top_videos = sorted_videos[:3]
        low_videos = sorted_videos[-3:] if len(sorted_videos) >= 6 else []

        # 4. اے آئی سے تفصیلی اردو تجزیہ اور تجاویز حاصل کریں
        ai_analysis = await ai_engine.analyze_channel_data(channel_data, recent_videos)

        audit_result = {
            "report_date": report_date,
            "period_start": period_start,
            "period_end": period_end,
            "channel_title": channel_data.get("title", settings.CHANNEL_NAME),
            "total_views": channel_data.get("views", 0),
            "total_subscribers": channel_data.get("subscribers", 0),
            "total_videos": channel_data.get("video_count", 0),
            "recent_videos_count": len(recent_videos),
            "top_videos": top_videos,
            "low_videos": low_videos,
            "ai_analysis": ai_analysis
        }

        return audit_result

audit_service = AuditService()
