import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import PostQueue, PostStatus, PostType
from agent_am.services.community_post_service import community_post_service

logger = logging.getLogger("agent_am.dispatcher_service")

class QueueDispatcher:
    """
    خودکار پبلشنگ ڈسپیچر برائے کوئز اور پول (Automated Post Dispatcher)
    پوسٹنگ قطار میں وقت مقررہ پر پہنچنے والی پوسٹس کو خودکار طور پر لائیو یوٹیوب پر شائع کرتا ہے۔
    """

    async def dispatch_due_posts(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        مقررہ وقت پر پہنچنے والی تمام مستند پوسٹس کو تلاش کر کے یوٹیوب پر شائع کرتا ہے
        """
        now_pkt = settings.now()
        # وہ پوسٹس جن کا وقت آ گیا ہے یا اگلے 2 منٹ کے اندر آنے والا ہے
        cutoff_time = now_pkt + timedelta(minutes=2)
        dispatched_count = 0
        results = []

        async with AsyncSessionLocal() as session:
            stmt = select(PostQueue).where(
                and_(
                    PostQueue.status.in_([PostStatus.VALIDATED, PostStatus.DRAFT]),
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
                try:
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

                    options = json.loads(post.options_json) if post.options_json else []
                    option_images = json.loads(post.images_json) if post.images_json else []
                    logger.info(f"یوٹیوب پر خودکار اشاعت شروع ہو رہی ہے: [{post.post_type.value}] {post.question_text[:40]}...")
                    
                    pub_res = await community_post_service.schedule_community_post(
                        post_type=post.post_type,
                        target_date=post.target_date,
                        scheduled_time=post.scheduled_time,
                        question=post.question_text,
                        options=options,
                        correct_answer=post.correct_answer,
                        explanation=post.explanation,
                        source_reference=post.source_reference,
                        image_path=post.image_path,
                        option_images=option_images,
                    )

                    if pub_res.get("success"):
                        post.status = PostStatus.PUBLISHED
                        post.external_post_id = pub_res.get("external_id")
                        dispatched_count += 1
                        logger.info(f"پوسٹ ID {post.id} کامیابی سے یوٹیوب پر لائیو ہو گئی! External ID: {post.external_post_id}")
                    else:
                        post.status = PostStatus.FAILED
                        post.last_error = pub_res.get("error")
                        logger.error(f"پوسٹ ID {post.id} کی اشاعت میں ناکامی: {post.last_error}")

                    await session.commit()
                    results.append({
                        "post_id": post.id,
                        "success": pub_res.get("success", False),
                        "external_id": pub_res.get("external_id")
                    })

                except Exception as e:
                    logger.error(f"ڈسپیچر پوسٹ ID {post.id} پر غیر متوقع استثناء: {str(e)}")
                    post.status = PostStatus.FAILED
                    post.last_error = str(e)
                    await session.commit()
                    results.append({"post_id": post.id, "success": False, "error": str(e)})

        return {
            "dispatched_count": dispatched_count,
            "results": results
        }

queue_dispatcher = QueueDispatcher()
