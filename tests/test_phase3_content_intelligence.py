"""
test_phase3_content_intelligence.py — Phase 3 Content Intelligence Tests
========================================================================
یہ ٹیسٹس چیک کرتے ہیں:
1. اردو اور عربی متن کی نارملائزیشن اور اعراب کا خاتمہ
2. SHA-256 فنگر پرنٹنگ کا یکساں نتیجہ (باوجود مختلف اعراب و اشکال)
3. سیمنٹک ٹوکن اوورلیپ (Jaccard Index)
4. ڈی ڈپلیکیٹر (ContentDeduplicator) کی فعالیت
5. اسلامی تاریخی موضوعات کی تصدیق شدہ فنگر پرنٹنگ اور تجاویز
6. 30 روزہ کونٹینٹ کیلنڈر کا مکمل جنریشن اور پانچوں زمروں میں متوازن تقسیم
7. اردو مارک ڈاؤن رپورٹ کا اندراج
"""

import pytest
import pytest_asyncio
from agent_am_growth.content_intelligence.fingerprint import (
    normalize_urdu_text,
    compute_content_fingerprint,
    tokenize_urdu,
    calculate_jaccard_similarity,
    content_deduplicator,
)
from agent_am_growth.content_intelligence.calendar_generator import (
    calendar_generator,
    CALENDAR_30_DAYS_BLUEPRINT,
)
from agent_am_growth.content_intelligence.topic_generator import (
    topic_generator,
    CURATED_TOPICS,
)
from agent_am_growth.content_intelligence.urdu_calendar_exporter import (
    urdu_calendar_exporter,
)
from agent_am.database.models import ContentCategory, ContentCalendarEntry, ContentTopicProposal


# ---------------------------------------------------------------------------
# Test 1: Urdu Normalization removes diacritics and unifies characters
# ---------------------------------------------------------------------------
def test_urdu_normalization():
    """اعراب اور مختلف حروف کا خاتمہ اور معیاری اردو متن"""
    text_with_diacritics = "سَیِّدُنَا مُحَمَّدٌ رَسُولُ اللَّهِ ﷺ"
    normalized = normalize_urdu_text(text_with_diacritics)

    # Tashkeel should be removed
    assert "َ" not in normalized
    assert "ِ" not in normalized
    assert "ُ" not in normalized
    assert "ّ" not in normalized
    assert "سیدنا محمد رسول اللہ" in normalized


def test_fingerprint_invariance_to_diacritics():
    """اعراب کے ساتھ اور بغیر دونوں عبارتوں کا ہیش ایک جیسا ہونا چاہیے"""
    text_plain = "غزوہ بدر حق اور باطل کا پہلا معرکہ"
    text_harakat = "غَزْوَةُ بَدْرٍ حَقٌّ اَوْرَ بَاطِلٌ کَا پَہْلَا مَعْرَکَہ"

    fp_plain = compute_content_fingerprint(text_plain)
    fp_harakat = compute_content_fingerprint(text_harakat)

    assert fp_plain == fp_harakat, "اعراب کے فرق سے ہیش نہیں بدلنا چاہیے"



# ---------------------------------------------------------------------------
# Test 2: Tokenization and Jaccard Similarity
# ---------------------------------------------------------------------------
def test_urdu_tokenization_and_jaccard():
    """مشابہ جملوں میں ٹوکن اوورلیپ کی درست شناخت"""
    sent1 = "حضرت عمر بن الخطاب کا قبول اسلام اور عدل و انصاف"
    sent2 = "حضرت عمر فاروق کا قبول اسلام اور بے مثال عدل"

    sim = calculate_jaccard_similarity(sent1, sent2)
    assert sim >= 0.40, f"مماثلت متوقع سے کم تھی: {sim}"


def test_jaccard_dissimilar():
    """بالکل مختلف موضوعات کی مشابہت کم ہونی چاہیے"""
    sent1 = "طوفان نوح اور کشتی کا واقعہ"
    sent2 = "معرکہ قادسیہ میں ایرانیوں کی شکست"

    sim = calculate_jaccard_similarity(sent1, sent2)
    assert sim <= 0.20, f"غیر متعلقہ جملوں کی مماثلت زیادہ نکلی: {sim}"


# ---------------------------------------------------------------------------
# Test 3: Curated Topics Seed & Integrity
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_seed_curated_proposals():
    """بنیادی اسلامی تاریخی موضوعات ڈیٹا بیس میں محفوظ ہوتے ہیں"""
    saved = await topic_generator.seed_curated_proposals()
    assert saved >= 0

    proposals = await topic_generator.get_all_proposals()
    assert len(proposals) >= len(CURATED_TOPICS)

    # تمام پانچوں زمروں کی موجودگی کی تصدیق
    categories_present = {p.category for p in proposals}
    assert ContentCategory.PROPHETS in categories_present
    assert ContentCategory.SEERAH in categories_present
    assert ContentCategory.COMPANIONS in categories_present
    assert ContentCategory.BATTLES_EVENTS in categories_present
    assert ContentCategory.AUDIENCE_QA in categories_present


# ---------------------------------------------------------------------------
# Test 4: Deduplicator detects exact topic duplicate
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_deduplicator_exact_match():
    """اگر موضوع پہلے سے موجود ہو تو ڈپلیکیٹ پکڑتا ہے"""
    await topic_generator.seed_curated_proposals()
    existing_topic = CURATED_TOPICS[0]["topic"]

    result = await content_deduplicator.check_similarity(existing_topic)
    assert result.is_duplicate is True
    assert result.similarity_score == 1.0


# ---------------------------------------------------------------------------
# Test 5: 30-Day Calendar Generator generates all 30 days
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_30_day_calendar_generation():
    """30 دن کا مکمل شیڈول تسلسل سے بنتا ہے"""
    count = await calendar_generator.generate_and_save_calendar()
    assert count == 30

    entries = await calendar_generator.get_calendar_entries()
    assert len(entries) == 30

    # دن 1 تا 30 کی تسلسل سے تصدیق
    days = [e.day_number for e in entries]
    assert days == list(range(1, 31))

    # تمام اندراجات میں کوئز اور پول موجود ہیں
    for e in entries:
        assert len(e.video_title_urdu) > 10
        assert len(e.quiz_proposal_urdu) > 15
        assert len(e.poll_proposal_urdu) > 15
        assert e.production_priority in ["HIGH", "MEDIUM", "LOW"]


# ---------------------------------------------------------------------------
# Test 6: 30-Day Calendar Balances All 5 Core Pillars
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_calendar_category_balance():
    """پانچوں بنیادی ستون کیلنڈر میں مناسب توازن کے ساتھ موجود ہیں"""
    entries = await calendar_generator.get_calendar_entries()
    counts = {}
    for e in entries:
        counts[e.category] = counts.get(e.category, 0) + 1

    assert counts.get(ContentCategory.PROPHETS, 0) >= 5
    assert counts.get(ContentCategory.SEERAH, 0) >= 5
    assert counts.get(ContentCategory.COMPANIONS, 0) >= 5
    assert counts.get(ContentCategory.BATTLES_EVENTS, 0) >= 5
    assert counts.get(ContentCategory.AUDIENCE_QA, 0) >= 4


# ---------------------------------------------------------------------------
# Test 7: Calendar Exporter generates markdown report
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_calendar_report_export(tmp_path):
    """اردو مارک ڈاؤن رپورٹ کامیابی سے بنتی ہے"""
    original_save = urdu_calendar_exporter._save_calendar_report

    def mock_save(md, today_str):
        path = str(tmp_path / f"test_calendar_{today_str}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        return path

    urdu_calendar_exporter._save_calendar_report = mock_save

    try:
        md = await urdu_calendar_exporter.export_calendar_report(save_to_file=True)
    finally:
        urdu_calendar_exporter._save_calendar_report = original_save

    assert "The Bayaan" in md
    assert "30 روزہ" in md
    assert "قصص الانبیاء" in md
    assert "غزوہ بدر" in md
    assert "6:15" in md
    assert "8:15" in md


