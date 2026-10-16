"""
comment_fetcher.py — Phase 4: YouTube Comments Fetcher
======================================================
The Bayaan چینل کے عوامی کمنٹس کو YouTube Data API v3 کے ذریعے
حاصل کرتا ہے اور ڈیٹا بیس میں محفوظ کرتا ہے۔

اصول و ضوابط:
- صرف مجاز اور عوامی طور پر دستیاب کمنٹس حاصل کیے جاتے ہیں
- API کوٹہ کی حد کا مکمل احترام
- کمنٹس کی تکرار کو روکنے کے لیے منفرد comment_id پر جانچ
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx
import pytz
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import (
    AudienceComment,
    CommentSentiment,
    DraftReplyStatus,
)

logger = logging.getLogger("agent_am.audience_manager.comment_fetcher")

PKT = pytz.timezone("Asia/Karachi")


class CommentFetcher:
    """
    YouTube Data API سے کمنٹس حاصل کرنے اور DB میں محفوظ کرنے کا ذمہ دار۔
    """

    YOUTUBE_COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"

    async def fetch_channel_comments(self, max_results: int = 50) -> Dict[str, Any]:
        """
        چینل کے کمنٹس حاصل کرے اور DB میں محفوظ کرے۔
        """
        if not settings.YOUTUBE_API_KEY or not settings.CHANNEL_ID:
            logger.warning("YouTube API Key یا Channel ID موجود نہیں")
            return {"success": False, "error": "API Key یا Channel ID غیر موجود ہے"}

        params = {
            "part": "snippet",
            "allThreadsRelatedToChannelId": settings.CHANNEL_ID,
            "key": settings.YOUTUBE_API_KEY,
            "maxResults": min(max_results, 100),
            "textFormat": "plainText",
            "order": "time",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.YOUTUBE_COMMENTS_URL, params=params)

            if response.status_code != 200:
                err_msg = f"YouTube API غلطی: {response.status_code} - {response.text[:200]}"
                logger.error(err_msg)
                return {"success": False, "error": err_msg}

            data = response.json()
            items = data.get("items", [])
            saved_count = 0

            async with AsyncSessionLocal() as session:
                for item in items:
                    top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    cid = item.get("id")
                    if not cid:
                        continue

                    author = top.get("authorDisplayName", "نامعلوم")
                    author_cid = top.get("authorChannelId", {}).get("value")
                    text = top.get("textDisplay", "").strip()
                    likes = int(top.get("likeCount", 0))
                    video_id = top.get("videoId")

                    pub_at = None
                    pub_str = top.get("publishedAt")
                    if pub_str:
                        try:
                            pub_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    # بنیادی سوالیہ انداز کی ابتدائی شناخت
                    is_q = any(q_mark in text for q_mark in ["?", "؟", "کیا", "کون", "کب", "کہاں", "کیوں", "کیسے"])

                    stmt = sqlite_insert(AudienceComment).values(
                        comment_id=cid,
                        author_name=author,
                        author_channel_id=author_cid,
                        text_original=text,
                        published_at=pub_at,
                        like_count=likes,
                        video_id=video_id,
                        is_question=is_q,
                        sentiment=CommentSentiment.QUESTION if is_q else CommentSentiment.NEUTRAL,
                        draft_status=DraftReplyStatus.DRAFT_ONLY,
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["comment_id"])
                    await session.execute(stmt)
                    saved_count += 1

                await session.commit()

            logger.info(f"{len(items)} کمنٹس میں سے {saved_count} کمنٹس کامیابی سے پروسیس ہوئے")
            return {
                "success": True,
                "fetched_count": len(items),
                "saved_count": saved_count,
            }

        except Exception as e:
            logger.exception(f"کمنٹس لانے کے دوران خرابی: {e}")
            return {"success": False, "error": str(e)}

    async def get_stored_comments(
        self, limit: int = 100, only_questions: bool = False
    ) -> List[AudienceComment]:
        """محفوظ شدہ کمنٹس حاصل کرے"""
        async with AsyncSessionLocal() as session:
            stmt = select(AudienceComment).order_by(AudienceComment.id.desc())
            if only_questions:
                stmt = stmt.where(AudienceComment.is_question == True)
            stmt = stmt.limit(limit)
            return list((await session.execute(stmt)).scalars().all())


# Singleton
comment_fetcher = CommentFetcher()
