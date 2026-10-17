import asyncio
import sys
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import PostQueue, PostStatus
from agent_am.services.community_post_service import community_post_service
from sqlalchemy import select

async def publish_tonight_poll():
    async with AsyncSessionLocal() as session:
        stmt = select(PostQueue).where(PostQueue.id == 2)
        post = (await session.execute(stmt)).scalars().first()
        if not post:
            print("Post ID 2 not found!")
            return
        
        print(f"Preparing to publish Post ID {post.id} ({post.post_type.value})...")
        print(f"Question: {post.question_text}")
        options = json.loads(post.options_json)
        print(f"Options: {options}")

        # Call service
        res = await community_post_service.schedule_community_post(
            post_type=post.post_type,
            target_date=post.target_date,
            scheduled_time=post.scheduled_time,
            question=post.question_text,
            options=options,
            correct_answer=post.correct_answer,
            explanation=post.explanation,
            source_reference=post.source_reference
        )

        print(f"Publish Result: {res}")
        if res.get("success"):
            post.status = PostStatus.PUBLISHED
            post.external_post_id = res.get("external_id")
            post.last_error = None
            await session.commit()
            print("Post ID 2 successfully committed as PUBLISHED!")
        else:
            post.status = PostStatus.FAILED
            post.last_error = res.get("error")
            await session.commit()
            print(f"Publish failed: {res.get('error')}")

if __name__ == "__main__":
    asyncio.run(publish_tonight_poll())
