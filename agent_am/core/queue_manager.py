import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import PostQueue, PostType, PostStatus
from agent_am.services.ai_engine import ai_engine
from agent_am.services.community_post_service import community_post_service
from agent_am.services.notification_service import notification_service

logger = logging.getLogger("agent_am.queue_manager")

class QueueManager:
    """
    رولنگ 24 تا 48 گھنٹے پوسٹنگ قطار کا منتظم (Queue Manager)
    ہر دن کے لیے ایک کوئز (Quiz) اور ایک ٹیکسٹ پول (Text Poll) کی تیاری اور شیڈولنگ کو یقینی بناتا ہے۔
    """

    async def get_upcoming_queue(self, days_ahead: int = 2) -> List[Dict[str, Any]]:
        """آئندہ دنوں کی قطار کا جائزہ لیتا ہے"""
        now_pkt = settings.now()
        start_date = now_pkt.strftime("%Y-%m-%d")
        end_date = (now_pkt + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        async with AsyncSessionLocal() as session:
            stmt = (
                select(PostQueue)
                .where(and_(PostQueue.target_date >= start_date, PostQueue.target_date <= end_date))
                .order_by(PostQueue.scheduled_time.asc())
            )
            res = await session.execute(stmt)
            records = res.scalars().all()
            
            output = []
            for r in records:
                output.append({
                    "id": r.id,
                    "post_type": r.post_type.value,
                    "target_date": r.target_date,
                    "scheduled_time": r.scheduled_time.strftime("%Y-%m-%d %I:%M %p"),
                    "question_text": r.question_text,
                    "options": json.loads(r.options_json) if r.options_json else [],
                    "correct_answer": r.correct_answer,
                    "explanation": r.explanation,
                    "source_reference": r.source_reference,
                    "image_path": r.image_path,
                    "images": json.loads(r.images_json) if r.images_json else [],
                    "status": r.status.value,
                    "external_post_id": r.external_post_id,
                    "retry_count": r.retry_count,
                    "last_error": r.last_error
                })
            return output

    async def replenish_queue(self, days_ahead: int = 2) -> Dict[str, Any]:
        """
        اگلے 24 سے 48 گھنٹوں کی جانچ کرتا ہے اور جو کوئز یا پول غائب ہوں انہیں تیار کر کے محفوظ کرتا ہے۔
        """
        now_pkt = settings.now()
        generated_count = 0
        scheduled_count = 0

        # حالیہ موضوعات لائیں تاکہ تکرار نہ ہو
        async with AsyncSessionLocal() as session:
            stmt = select(PostQueue.question_text).order_by(PostQueue.id.desc()).limit(20)
            res = await session.execute(stmt)
            recent_questions = res.scalars().all()

        for day_offset in range(days_ahead):
            target_dt = now_pkt + timedelta(days=day_offset)
            target_date_str = target_dt.strftime("%Y-%m-%d")

            import random
            # 1. کوئز کا وقت: سوا 6 بجے (18:15 PST) مع قدرتی تغیر (±15 منٹ بمطابق 6:00 تا 6:45 PM)
            quiz_jitter_minutes = random.choice([0, -10, 10, -15, 15])
            quiz_time = target_dt.replace(hour=18, minute=15, second=0, microsecond=0) + timedelta(minutes=quiz_jitter_minutes)
            
            # 2. پول کا وقت: سوا 8 بجے (20:15 PST) مع قدرتی تغیر (±15 منٹ بمطابق 8:00 تا 8:45 PM)
            poll_jitter_minutes = random.choice([0, -10, 10, -15, 15])
            poll_time = target_dt.replace(hour=20, minute=15, second=0, microsecond=0) + timedelta(minutes=poll_jitter_minutes)

            # کوئز چیک کریں
            quiz_exists = await self._is_post_present(target_date_str, PostType.QUIZ)
            if not quiz_exists:
                logger.info(f"تاریخ {target_date_str} کے لیے کوئز موجود نہیں تھا۔ نیا کوئز تیار کیا جا رہا ہے۔")
                quiz_data = await ai_engine.generate_quiz(recent_topics=recent_questions)
                await self._save_and_schedule_post(
                    post_type=PostType.QUIZ,
                    target_date=target_date_str,
                    scheduled_time=quiz_time,
                    data=quiz_data
                )
                generated_count += 1

            # پول چیک کریں
            poll_exists = await self._is_post_present(target_date_str, PostType.POLL)
            if not poll_exists:
                logger.info(f"تاریخ {target_date_str} کے لیے پول موجود نہیں تھا۔ نیا پول تیار کیا جا رہا ہے۔")
                poll_data = await ai_engine.generate_poll(recent_topics=recent_questions)
                await self._save_and_schedule_post(
                    post_type=PostType.POLL,
                    target_date=target_date_str,
                    scheduled_time=poll_time,
                    data=poll_data
                )
                generated_count += 1

        return {
            "status": "success",
            "generated_count": generated_count,
            "scheduled_count": scheduled_count
        }

    async def _is_post_present(self, target_date: str, post_type: PostType) -> bool:
        """چیک کرتا ہے کہ مخصوص تاریخ اور قسم کی پوسٹ پہلے سے موجود ہے یا نہیں"""
        async with AsyncSessionLocal() as session:
            stmt = select(PostQueue).where(
                and_(PostQueue.target_date == target_date, PostQueue.post_type == post_type)
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none() is not None

    async def _save_and_schedule_post(
        self,
        post_type: PostType,
        target_date: str,
        scheduled_time: datetime,
        data: Dict[str, Any]
    ) -> PostQueue:
        """نئی پوسٹ کو محفوظ کر کے شیڈول کرتا ہے"""
        content_hash = data.get("content_hash") or ai_engine.compute_content_hash(data["question"], data["options"])

        options = data.get("options", [])
        image_path = data.get("image_path")
        option_images = data.get("option_images", [])

        # شیڈولنگ سروس کو کال کریں
        sched_res = await community_post_service.schedule_community_post(
            post_type=post_type,
            target_date=target_date,
            scheduled_time=scheduled_time,
            question=data["question"],
            options=options,
            correct_answer=data.get("correct_answer"),
            explanation=data.get("explanation"),
            source_reference=data.get("source_reference"),
            image_path=image_path,
            option_images=option_images,
        )

        async with AsyncSessionLocal() as session:
            post_item = PostQueue(
                post_type=post_type,
                target_date=target_date,
                scheduled_time=scheduled_time,
                question_text=data["question"],
                options_json=json.dumps(options, ensure_ascii=False),
                correct_answer=data.get("correct_answer"),
                explanation=data.get("explanation"),
                source_reference=data.get("source_reference"),
                image_path=image_path,
                images_json=json.dumps(option_images, ensure_ascii=False) if option_images else None,
                content_hash=content_hash,
                status=sched_res.get("status", PostStatus.DRAFT),
                external_post_id=sched_res.get("external_id"),
                last_error=sched_res.get("error")
            )
            session.add(post_item)
            await session.commit()
            await session.refresh(post_item)

            if sched_res.get("success"):
                await notification_service.notify_post_scheduled(
                    post_type=post_type.value,
                    target_date=target_date,
                    post_time=scheduled_time.strftime("%I:%M %p PST"),
                    question=data["question"]
                )

            return post_item

queue_manager = QueueManager()
