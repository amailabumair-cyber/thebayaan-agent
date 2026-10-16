import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import PostQueue, PostStatus, PostType
from agent_am.services.community_post_service import community_post_service
from agent_am_growth.reliability.idempotency import idempotency_guard
from agent_am_growth.reliability.retry_handler import retry_handler, TaskExecutionState
from agent_am_growth.reliability.structured_logger import structured_logger
from agent_am_growth.reliability.backup_manager import backup_manager

logger = logging.getLogger("agent_am.queue_dispatcher")

class QueueDispatcher:
    """
    خودکار پبلشنگ ڈسپیچر (Automated Post Dispatcher)
    پوسٹنگ قطار میں وقت مقررہ پر پہنچنے والی پوسٹس کو خودکار طور پر لائیو یوٹیوب پر شائع کرتا ہے۔
    """

    async def dispatch_due_posts(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        مقررہ وقت پر پہنچنے والی تمام مستند پوسٹس کو تلاش کر کے شائع کرتا ہے
        """
        now_pkt = settings.now()
        # وہ پوسٹس جو اب یا اگلے 2 منٹ کے اندر شائع ہونی ہیں
        cutoff_time = now_pkt + timedelta(minutes=2)
        dispatched_count = 0
        results = []

        async with AsyncSessionLocal() as session:
            stmt = select(PostQueue).where(
                and_(
                    PostQueue.status == PostStatus.VALIDATED,
                    PostQueue.scheduled_time <= cutoff_time
                )
            ).order_by(PostQueue.scheduled_time.asc())
            res = await session.execute(stmt)
            due_posts = res.scalars().all()

        if not due_posts:
            return {
                "dispatched_count": 0,
                "message": "کوئی پوسٹ اس وقت اشاعت کے لیے زیرِ التواء نہیں ہے۔",
                "results": []
            }

        logger.info(f"ڈسپیچر: {len(due_posts)} پوسٹس اشاعت کے لیے تیار پائی گئیں۔")

        for post in due_posts:
            # 1. آئیڈیمپوٹینسی چیک (کیا یہ پہلے شائع ہو چکی ہے؟)
            can_pub, reason = await idempotency_guard.can_publish(
                target_date=post.target_date,
                post_type=post.post_type,
                content_hash=post.content_hash,
                post_id=post.id
            )

            if not can_pub:
                logger.warning(f"پوسٹ ID {post.id} کو مسترد کر دیا گیا: {reason}")
                results.append({
                    "post_id": post.id,
                    "success": False,
                    "reason": reason
                })
                continue

            # لاک حاصل کریں
            if not idempotency_guard.acquire_lock(post.target_date, post.post_type):
                logger.info(f"پوسٹ ID {post.id} پہلے ہی پراسیس ہو رہی ہے۔ اسکوپ محفوظ۔")
                continue

            try:
                # 2. اگر ڈرائے رن (Dry Run) موڈ فعال ہو تو بغیر یوٹیوب پر پوسٹ کیے جانچیں
                if dry_run:
                    logger.info(f"[DRY-RUN] پوسٹ ID {post.id} کی فرضی اشاعت کامیاب سمجھی گئی۔")
                    results.append({
                        "post_id": post.id,
                        "success": True,
                        "mode": "DRY_RUN",
                        "question": post.question_text
                    })
                    dispatched_count += 1
                    continue

                # 3. اشاعت سے پہلے ڈیٹا بیس کا ایک خودکار فوری بیک اپ
                backup_manager.create_backup(label=f"pre_pub_{post.id}")

                # 4. ری ٹرائی ہینڈلر کے ساتھ پبلش سروس کو کال کریں
                async def _do_publish():
                    options = json.loads(post.options_json)
                    return await community_post_service.schedule_community_post(
                        post_type=post.post_type,
                        target_date=post.target_date,
                        scheduled_time=post.scheduled_time,
                        question=post.question_text,
                        options=options,
                        correct_answer=post.correct_answer,
                        explanation=post.explanation,
                        source_reference=post.source_reference
                    )

                state, pub_res, err = await retry_handler.execute_with_retry(
                    task_name=f"publish_post_{post.id}_{post.post_type.value}",
                    coro_fn=_do_publish,
                    max_retries=3
                )

                if state == TaskExecutionState.SUCCESS and pub_res and pub_res.get("success"):
                    ext_id = pub_res.get("external_id", f"yt_live_{int(now_pkt.timestamp())}")
                    async with AsyncSessionLocal() as session:
                        stmt_u = select(PostQueue).where(PostQueue.id == post.id)
                        res_u = await session.execute(stmt_u)
                        item = res_u.scalar_one_or_none()
                        if item:
                            item.status = PostStatus.PUBLISHED
                            item.external_post_id = ext_id
                            item.last_error = None
                            await session.commit()

                    dispatched_count += 1
                    results.append({
                        "post_id": post.id,
                        "success": True,
                        "external_id": ext_id
                    })
                    structured_logger.log_event(
                        event_type="POST_PUBLISHED_LIVE",
                        task_name=f"post_{post.id}",
                        status="PUBLISHED",
                        details_urdu=f"پوسٹ ({post.post_type.value}) کامیابی سے یوٹیوب پر لائیو شائع ہو گئی: {post.question_text[:50]}..."
                    )
                else:
                    async with AsyncSessionLocal() as session:
                        stmt_u = select(PostQueue).where(PostQueue.id == post.id)
                        res_u = await session.execute(stmt_u)
                        item = res_u.scalar_one_or_none()
                        if item:
                            item.retry_count = (item.retry_count or 0) + 1
                            item.last_error = err or "اشاعت مکمل نہیں ہو سکی"
                            await session.commit()

                    results.append({
                        "post_id": post.id,
                        "success": False,
                        "error": err
                    })

            finally:
                idempotency_guard.release_lock(post.target_date, post.post_type)

        return {
            "dispatched_count": dispatched_count,
            "results": results
        }

queue_dispatcher = QueueDispatcher()
