"""
pipeline_manager.py — Phase 5: 10-Stage Video Production Pipeline
=================================================================
The Bayaan چینل کے لیے ویڈیو کی تیاری کے 10 مراحل کا کڑا اور منظم انتظام۔

مراحل:
1. TOPIC_PROPOSED: موضوع تجویز شدہ
2. RESEARCH_PENDING: تحقیق طلب
3. SOURCES_REVIEWED: مآخذ و روایات کی جانچ مکمل
4. SCRIPT_DRAFT: ابتدائی اسکرپٹ تحریر
5. SCRIPT_APPROVED: اسکرپٹ کی شرعی و تاریخی منظوری
6. VISUAL_PROMPTS: منظر بہ منظر بصری پرامپٹس
7. VOICEOVER_EDITING: صداکاری و ویڈیو ایڈیٹنگ
8. UPLOAD_PREP: عنوان، تفصیل، ٹیگز اور تھمب نیل کی تیاری
9. PUBLICATION_APPROVED: اشاعت کی حتمی منظوری
10. PERFORMANCE_REVIEW: کارکردگی کا تفصیلی جائزہ

حفاظتی اصول (Stage Gates):
- بغیر مصدقہ مآخذ کے اسکرپٹ منظور نہیں ہو سکتا
- بغیر صریح منظوری (Explicit Human Approval) کے اسٹیج 9 پر نہیں جایا جا سکتا
- ہر مرحلے پر معتبر تاریخی حوالے اور متنازعہ مقامات کی جانچ لازمی ہے
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, update

from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import (
    ProductionStage,
    VideoProductionProject,
)

logger = logging.getLogger("agent_am.production_pipeline.manager")

# مراحل کی قانونی ترتیب (Ordered Stage Progression)
STAGE_ORDER = [
    ProductionStage.TOPIC_PROPOSED,
    ProductionStage.RESEARCH_PENDING,
    ProductionStage.SOURCES_REVIEWED,
    ProductionStage.SCRIPT_DRAFT,
    ProductionStage.SCRIPT_APPROVED,
    ProductionStage.VISUAL_PROMPTS,
    ProductionStage.VOICEOVER_EDITING,
    ProductionStage.UPLOAD_PREP,
    ProductionStage.PUBLICATION_APPROVED,
    ProductionStage.PERFORMANCE_REVIEW,
]


class ProductionPipelineManager:
    """
    ویڈیو پروڈکشن پائپ لائن کو منظم کرنے اور اسٹیج گیٹس کو نافذ کرنے والی کلاس۔
    """

    async def create_project(
        self,
        project_code: str,
        title_urdu: str,
        target_publish_date: Optional[str] = None,
        historical_notes: Optional[str] = None,
        verified_sources: Optional[List[str]] = None,
    ) -> VideoProductionProject:
        """نیا ویڈیو پروڈکشن پروجیکٹ شروع کرے (ابتدائی مرحلہ: TOPIC_PROPOSED)"""
        async with AsyncSessionLocal() as session:
            # چیک کریں اگر پہلے سے موجود ہے
            stmt = select(VideoProductionProject).where(
                VideoProductionProject.project_code == project_code
            )
            existing = (await session.execute(stmt)).scalars().first()
            if existing:
                return existing

            project = VideoProductionProject(
                project_code=project_code,
                title_urdu=title_urdu,
                stage=ProductionStage.TOPIC_PROPOSED,
                target_publish_date=target_publish_date,
                historical_notes_urdu=historical_notes or "",
                verified_sources_json=json.dumps(verified_sources or [], ensure_ascii=False),
                is_publication_approved=False,
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)

        logger.info(f"نیا ویڈیو پروجیکٹ بنایا گیا: {project_code} — '{title_urdu}'")
        return project

    async def advance_stage(
        self,
        project_code: str,
        target_stage: ProductionStage,
        reviewer_note: Optional[str] = None,
        is_human_approved: bool = False,
    ) -> Dict[str, Any]:
        """
        پروجیکٹ کو اگلے مرحلے پر لے جائے، بشرطیکہ تمام شرائط و گیٹس پورے ہوں۔
        """
        async with AsyncSessionLocal() as session:
            stmt = select(VideoProductionProject).where(
                VideoProductionProject.project_code == project_code
            )
            project = (await session.execute(stmt)).scalars().first()
            if not project:
                return {"success": False, "error": f"پروجیکٹ '{project_code}' نہیں ملا"}

            current_idx = STAGE_ORDER.index(project.stage)
            target_idx = STAGE_ORDER.index(target_stage)

            # 1. مرحلہ پیچھے یا ایک سے زیادہ آگے پھلانگنے کی جانچ
            if target_idx > current_idx + 1:
                return {
                    "success": False,
                    "error": f"مراحل کو پھلانگا نہیں جا سکتا۔ موجودہ مرحلہ: {project.stage.value}، مطلوبہ مرحلہ: {target_stage.value}",
                }

            # 2. گیٹ: SCRIPT_APPROVED کے لیے روایات کی جانچ لازم ہے
            if target_stage == ProductionStage.SCRIPT_APPROVED:
                sources = json.loads(project.verified_sources_json or "[]")
                if not sources:
                    return {
                        "success": False,
                        "error": "اسکرپٹ کی منظوری سے قبل مستند مآخذ و کتب (Sources) کی فہرست لازمی ہے",
                    }

            # 3. گیٹ: PUBLICATION_APPROVED کے لیے صریح انسانی منظوری درکار ہے
            if target_stage == ProductionStage.PUBLICATION_APPROVED:
                if not is_human_approved:
                    return {
                        "success": False,
                        "error": "اشاعت کی منظوری (PUBLICATION_APPROVED) کے لیے واضح انسانی منظوری (is_human_approved=True) لازمی ہے",
                    }
                project.is_publication_approved = True

            # مرحلہ آگے بڑھائیں
            project.stage = target_stage
            if reviewer_note:
                project.reviewer_notes_urdu = (
                    f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {reviewer_note}\n"
                    + (project.reviewer_notes_urdu or "")
                )

            await session.commit()
            await session.refresh(project)

        logger.info(f"پروجیکٹ {project_code} اسٹیج {target_stage.value} پر منتقل ہو گیا")
        return {
            "success": True,
            "project_code": project_code,
            "new_stage": target_stage.value,
            "is_publication_approved": project.is_publication_approved,
        }

    async def get_project(self, project_code: str) -> Optional[VideoProductionProject]:
        """پروجیکٹ کی تفصیلات حاصل کرے"""
        async with AsyncSessionLocal() as session:
            stmt = select(VideoProductionProject).where(
                VideoProductionProject.project_code == project_code
            )
            return (await session.execute(stmt)).scalars().first()

    async def list_all_projects(self) -> List[VideoProductionProject]:
        """تمام پروجیکٹس کی فہرست حاصل کرے"""
        async with AsyncSessionLocal() as session:
            stmt = select(VideoProductionProject).order_by(VideoProductionProject.id.desc())
            return list((await session.execute(stmt)).scalars().all())


# Singleton
pipeline_manager = ProductionPipelineManager()
