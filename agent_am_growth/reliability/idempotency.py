import asyncio
import logging
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import select, and_
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import PostQueue, PostStatus, PostType
from agent_am_growth.reliability.structured_logger import structured_logger

logger = logging.getLogger("agent_am.idempotency")

class IdempotencyGuard:
    """
    ڈپلیکیٹ اشاعت کی کڑی روک تھام (Idempotency & Duplicate Prevention)
    اس بات کو 100% یقینی بناتا ہے کہ کوئی کوئز یا پول ایک ہی دن دو بار یا پہلے سے شائع شدہ حالت میں دوبارہ پوسٹ نہ ہو۔
    """

    def __init__(self):
        # میموری لاک برائے کنکرنسی سیفٹی
        self._lock = asyncio.Lock()
        self._in_progress_posts = set()

    async def can_publish(
        self,
        target_date: str,
        post_type: PostType,
        content_hash: str,
        post_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        چیک کرتا ہے کہ آیا یہ پوسٹ شائع کی جا سکتی ہے یا یہ پہلے سے شائع ہو چکی ہے
        """
        async with self._lock:
            # 1. کیا یہ پوسٹ اس وقت ایگزیکیوشن میں ہے؟
            post_key = f"{target_date}_{post_type.value}"
            if post_key in self._in_progress_posts:
                return False, f"پوسٹ ({post_key}) فی الوقت شائع ہونے کے عمل میں ہے۔ متوازی کوشش بلاک کر دی گئی۔"

            async with AsyncSessionLocal() as session:
                # 2. کیا اس تاریخ پر اس قسم کی کوئی پوسٹ پہلے سے PUBLISHED ہے؟
                stmt_published = select(PostQueue).where(
                    and_(
                        PostQueue.target_date == target_date,
                        PostQueue.post_type == post_type,
                        PostQueue.status == PostStatus.PUBLISHED
                    )
                )
                res = await session.execute(stmt_published)
                already_pub = res.scalar_one_or_none()
                if already_pub:
                    return False, f"تاریخ {target_date} کے لیے {post_type.value} پہلے ہی شائع ہو چکا ہے (External ID: {already_pub.external_post_id})۔"

                # 3. کیا یہ مواد (Content Hash) تاریخی طور پر پہلے کسی بھی تاریخ پر شائع ہوا ہے؟
                stmt_hash = select(PostQueue).where(
                    and_(
                        PostQueue.content_hash == content_hash,
                        PostQueue.status == PostStatus.PUBLISHED
                    )
                )
                res_hash = await session.execute(stmt_hash)
                dup_content = res_hash.scalar_one_or_none()
                if dup_content and (post_id is None or dup_content.id != post_id):
                    return False, f"یہ سوال تاریخی ریکارڈ میں پہلے ہی تاریخ {dup_content.target_date} کو شائع ہو چکا ہے۔ تکرار ممنوع ہے۔"

                # 4. اگر مخصوص پوسٹ آئی ڈی دی گئی ہے تو اس کی موجودہ حالت چیک کریں
                if post_id is not None:
                    stmt_item = select(PostQueue).where(PostQueue.id == post_id)
                    res_item = await session.execute(stmt_item)
                    item = res_item.scalar_one_or_none()
                    if item and item.status == PostStatus.PUBLISHED:
                        return False, f"پوسٹ ID {post_id} پہلے ہی شائع شدہ ہے۔"

            return True, "پوسٹ تصدیق شدہ ہے اور اشاعت کے لیے مکمل محفوظ ہے۔"

    def acquire_lock(self, target_date: str, post_type: PostType) -> bool:
        """پوسٹ کو پراسیسنگ حالت میں لاک کرتا ہے"""
        key = f"{target_date}_{post_type.value}"
        if key in self._in_progress_posts:
            return False
        self._in_progress_posts.add(key)
        return True

    def release_lock(self, target_date: str, post_type: PostType):
        """پوسٹ کا لاک کھولتا ہے"""
        key = f"{target_date}_{post_type.value}"
        self._in_progress_posts.discard(key)

idempotency_guard = IdempotencyGuard()
