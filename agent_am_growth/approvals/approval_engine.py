"""
approval_engine.py — Phase 6: Human Approval State Machine
==========================================================
The Bayaan چینل کے لیے سخت اور شفاف انسانی منظوری کا ورک فلو۔

ریاستیں (7 Approval States):
1. PENDING: زیر التواء (نئی کارروائی منظوری کی منتظر)
2. APPROVED: منظور شدہ (ایڈمن نے اجازت دے دی)
3. REJECTED: مسترد (ایڈمن نے انکار کر دیا)
4. CHANGES_REQUESTED: ترمیم درکار (ایڈمن نے تبدیلی کا نوٹ لکھا)
5. EXECUTING: عمل جاری (منظور شدہ کام انجام دیا جا رہا ہے)
6. COMPLETED: مکمل شدہ (کامیابی سے پایہ تکمیل کو پہنچا)
7. FAILED: ناکام رہا (عمل درآمد میں تکنیکی خرابی آئی)

بنیادی قانون:
- ہر منظوری صرف اس مخصوص آئٹم اور صریح ہدف کے لیے کارآمد ہوگی
- ایک آئٹم کی منظوری سے کسی دوسرے غیر متعلقہ عمل کو اختیار نہیں ملے گا
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import pytz
from sqlalchemy import select

from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import (
    ApprovalState,
    ApprovalActionType,
    ApprovalItem,
)

logger = logging.getLogger("agent_am.approvals.engine")

PKT = pytz.timezone("Asia/Karachi")

# جائز ریاستی تغیرات (Valid State Transitions)
VALID_TRANSITIONS = {
    ApprovalState.PENDING: [ApprovalState.APPROVED, ApprovalState.REJECTED, ApprovalState.CHANGES_REQUESTED],
    ApprovalState.CHANGES_REQUESTED: [ApprovalState.PENDING, ApprovalState.REJECTED],
    ApprovalState.APPROVED: [ApprovalState.EXECUTING, ApprovalState.REJECTED],
    ApprovalState.EXECUTING: [ApprovalState.COMPLETED, ApprovalState.FAILED],
    ApprovalState.FAILED: [ApprovalState.PENDING, ApprovalState.REJECTED],
    ApprovalState.REJECTED: [],  # فائنل
    ApprovalState.COMPLETED: [], # فائنل
}


class ApprovalEngine:
    """
    منظوریوں کی قطار کو سنبھالنے اور ریاستی مشین کو کنٹرول کرنے والی کلاس۔
    """

    async def submit_for_approval(
        self,
        item_type: ApprovalActionType,
        target_reference_id: str,
        title_urdu: str,
        action_details_urdu: str,
    ) -> ApprovalItem:
        """نیا آئٹم منظوری کی قطار میں داخل کرے (PENDING)"""
        async with AsyncSessionLocal() as session:
            # اگر پہلے سے پینڈنگ ہے تو وہی واپس کریں
            stmt = select(ApprovalItem).where(
                ApprovalItem.item_type == item_type,
                ApprovalItem.target_reference_id == target_reference_id,
                ApprovalItem.state == ApprovalState.PENDING,
            )
            existing = (await session.execute(stmt)).scalars().first()
            if existing:
                return existing

            item = ApprovalItem(
                item_type=item_type,
                target_reference_id=target_reference_id,
                title_urdu=title_urdu,
                action_details_urdu=action_details_urdu,
                state=ApprovalState.PENDING,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)

        logger.info(f"نئی منظوری کی درخواست درج: [{item_type.value}] {target_reference_id} — '{title_urdu}'")
        return item

    async def transition_state(
        self,
        item_id: int,
        target_state: ApprovalState,
        reviewer_note: Optional[str] = None,
        actioned_by: str = "Admin",
    ) -> Dict[str, Any]:
        """
        کسی آئٹم کی حالت کو تبدیل کرے (مثلاً PENDING -> APPROVED)۔
        """
        async with AsyncSessionLocal() as session:
            stmt = select(ApprovalItem).where(ApprovalItem.id == item_id)
            item = (await session.execute(stmt)).scalars().first()
            if not item:
                return {"success": False, "error": f"منظوری آئٹم ID {item_id} نہیں ملا"}

            current_state = item.state
            allowed = VALID_TRANSITIONS.get(current_state, [])

            if target_state not in allowed:
                return {
                    "success": False,
                    "error": f"ریاست '{current_state.value}' سے '{target_state.value}' میں تبدیلی کی اجازت نہیں ہے",
                }

            # حالت تبدیل کریں
            item.state = target_state
            item.actioned_by = actioned_by
            item.actioned_at = datetime.utcnow()
            if reviewer_note:
                item.reviewer_note_urdu = (
                    f"[{datetime.now(PKT).strftime('%Y-%m-%d %I:%M %p')}] {reviewer_note}\n"
                    + (item.reviewer_note_urdu or "")
                )

            # اگر ویڈیو پبلیکیشن منظور ہوئی ہو تو پروڈکشن پائپ لائن سے لنک کریں
            if item.item_type == ApprovalActionType.VIDEO_PUBLICATION and target_state == ApprovalState.APPROVED:
                from agent_am_growth.production_pipeline.pipeline_manager import pipeline_manager
                from agent_am.database.models import ProductionStage
                await pipeline_manager.advance_stage(
                    project_code=item.target_reference_id,
                    target_stage=ProductionStage.PUBLICATION_APPROVED,
                    reviewer_note=reviewer_note,
                    is_human_approved=True,
                )

            await session.commit()
            await session.refresh(item)

        logger.info(f"آئٹم {item_id} کامیابی سے {target_state.value} پر منتقل ہوا")
        return {
            "success": True,
            "item_id": item_id,
            "new_state": target_state.value,
            "target_reference_id": item.target_reference_id,
            "action_details": item.action_details_urdu,
        }

    async def list_items(
        self, state: Optional[ApprovalState] = None
    ) -> List[ApprovalItem]:
        """منظوری کے آئٹمز کی فہرست واپس کرے"""
        async with AsyncSessionLocal() as session:
            stmt = select(ApprovalItem).order_by(ApprovalItem.id.desc())
            if state:
                stmt = stmt.where(ApprovalItem.state == state)
            return list((await session.execute(stmt)).scalars().all())


# Singleton
approval_engine = ApprovalEngine()
