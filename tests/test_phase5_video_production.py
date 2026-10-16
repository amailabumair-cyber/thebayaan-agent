"""
test_phase5_video_production.py — Phase 5 Video Production Pipeline Tests
========================================================================
یہ ٹیسٹس چیک کرتے ہیں:
1. ویڈیو پروڈکشن کے تمام 10 مراحل کی درست قانونی ترتیب
2. اسٹیج گیٹس: بغیر مآخذ اسکرپٹ منظور نہیں ہو سکتا
3. اشاعت کا کڑا گیٹ: بغیر صریح انسانی منظوری اشاعت ناممکن
4. مراحل کو پھلانگنے کی ممانعت
5. فلیگ شپ پروجیکٹ کا قیام اور تمام اجزاء (ہوک، اسکرپٹ، بصری پرامپٹس، چیک لسٹ)
6. پروڈکشن پیکیج کی اردو مارک ڈاؤن رپورٹ کا برآمد ہونا
"""

import pytest
import pytest_asyncio
from agent_am.database.models import (
    ProductionStage,
    VideoProductionProject,
)
from agent_am_growth.production_pipeline.pipeline_manager import (
    pipeline_manager,
    STAGE_ORDER,
)
from agent_am_growth.production_pipeline.script_builder import (
    script_builder,
    FLAGSHIP_BADR_PACKAGE,
)
from agent_am_growth.production_pipeline.urdu_production_exporter import (
    urdu_production_exporter,
)


# ---------------------------------------------------------------------------
# Test 1: Stage Order & Count
# ---------------------------------------------------------------------------
def test_production_stages_count_and_order():
    """10 مراحل کی مکمل اور درست ترتیب"""
    assert len(STAGE_ORDER) == 10
    assert STAGE_ORDER[0] == ProductionStage.TOPIC_PROPOSED
    assert STAGE_ORDER[4] == ProductionStage.SCRIPT_APPROVED
    assert STAGE_ORDER[8] == ProductionStage.PUBLICATION_APPROVED
    assert STAGE_ORDER[9] == ProductionStage.PERFORMANCE_REVIEW


# ---------------------------------------------------------------------------
# Test 2: Project Creation in Initial Stage
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_project_creation():
    """نیا پروجیکٹ ابتدائی مرحلے (TOPIC_PROPOSED) پر بنتا ہے"""
    p = await pipeline_manager.create_project(
        project_code="TEST-001",
        title_urdu="ٹیسٹ پروجیکٹ: حضرت نوح علیہ السلام کی کشتی",
        historical_notes="قرآنی آیات اور تفاسیر",
        verified_sources=["سورۃ ہود", "تفسیر ابن کثیر"],
    )
    assert p.project_code == "TEST-001"
    assert p.stage == ProductionStage.TOPIC_PROPOSED
    assert p.is_publication_approved is False


# ---------------------------------------------------------------------------
# Test 3: Stage Progression & Skipping Prevention
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stage_skipping_prevented():
    """مراحل کو پھلانگنا روکا جاتا ہے"""
    res = await pipeline_manager.advance_stage(
        project_code="TEST-001",
        target_stage=ProductionStage.SCRIPT_APPROVED,  # اسٹیج 0 سے سیدھا اسٹیج 4
    )
    assert res["success"] is False
    assert "پھلانگا نہیں جا سکتا" in res["error"]


# ---------------------------------------------------------------------------
# Test 4: Gate - Script Approval Requires Sources
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_script_approval_requires_sources():
    """بغیر مآخذ کے اسکرپٹ منظور نہیں ہو سکتا"""
    p_nosource = await pipeline_manager.create_project(
        project_code="TEST-NOSOURCE",
        title_urdu="بغیر مآخذ کا فرضی عنوان",
        verified_sources=[],
    )
    # پہلے اگلے مرحلے پر لے جائیں
    await pipeline_manager.advance_stage("TEST-NOSOURCE", ProductionStage.RESEARCH_PENDING)
    await pipeline_manager.advance_stage("TEST-NOSOURCE", ProductionStage.SOURCES_REVIEWED)
    await pipeline_manager.advance_stage("TEST-NOSOURCE", ProductionStage.SCRIPT_DRAFT)

    # اب SCRIPT_APPROVED کی کوشش کریں
    res = await pipeline_manager.advance_stage("TEST-NOSOURCE", ProductionStage.SCRIPT_APPROVED)
    assert res["success"] is False
    assert "مستند مآخذ" in res["error"]


# ---------------------------------------------------------------------------
# Test 5: Publication Gate - Requires Explicit Human Approval
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_publication_gate_strict_human_approval():
    """بغیر صریح انسانی منظوری کے اشاعت کا مرحلہ نہیں آ سکتا"""
    # فلیگ شپ پروجیکٹ VPP-001 اسٹیج 7 (UPLOAD_PREP) پر ہے
    await script_builder.seed_flagship_project()

    # بغیر منظوری کی کوشش:
    fail_res = await pipeline_manager.advance_stage(
        project_code="VPP-001",
        target_stage=ProductionStage.PUBLICATION_APPROVED,
        is_human_approved=False,
    )
    assert fail_res["success"] is False
    assert "واضح انسانی منظوری" in fail_res["error"]

    # صریح انسانی منظوری کے ساتھ:
    pass_res = await pipeline_manager.advance_stage(
        project_code="VPP-001",
        target_stage=ProductionStage.PUBLICATION_APPROVED,
        reviewer_note="ایڈمن نے ویڈیو دیکھ کر حتمی اشاعت کی منظوری دی",
        is_human_approved=True,
    )
    assert pass_res["success"] is True
    assert pass_res["is_publication_approved"] is True


# ---------------------------------------------------------------------------
# Test 6: Flagship Project Structure & Export
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_flagship_project_and_export(tmp_path):
    """فلیگ شپ پروجیکٹ کے تمام اجزاء اور مارک ڈاؤن رپورٹ کا برآمد ہونا"""
    original_save = urdu_production_exporter._save_production_report

    def mock_save(md, pcode):
        path = str(tmp_path / f"prod_test_{pcode}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        return path

    urdu_production_exporter._save_production_report = mock_save

    try:
        md = await urdu_production_exporter.export_production_package("VPP-001", save_to_file=True)
    finally:
        urdu_production_exporter._save_production_report = original_save

    assert "The Bayaan" in md
    assert "VPP-001" in md
    assert "صحیح بخاری" in md
    assert "صحیح مسلم" in md
    assert "منظر بہ منظر" in md
    assert "صداکاری و ایڈیٹنگ" in md
