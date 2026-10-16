"""
fingerprint.py — Phase 3: Content Fingerprinting & Semantic Deduplication
========================================================================
اردو اور عربی عبارتوں کی نارملائزیشن، SHA-256 ہیشنگ، اور موضوعات
کی تکرار (Duplicate Detection) کی جامع جانچ۔

اہم خصوصیات:
- اعراب و علامات (تذکیر، حرکات، تطویل) کا خاتمہ
- اردو حروف کی معیاری ساخت (الف، ی، ہ، ک وغیرہ)
- SHA-256 بنیاد پر سخت برابری کی جانچ
- ٹوکن سیٹ بنیاد پر معنوی مشابہت (Jaccard Overlap) تاکہ مختلف الفاظ میں ایک ہی مفہوم پکڑا جا سکے
"""

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Set

from sqlalchemy import select

from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import (
    VideoSnapshot,
    GrowthVideoSnapshot,
    PostQueue,
    ContentTopicProposal,
)


# ---------------------------------------------------------------------------
# Urdu / Arabic Normalization Regexes
# ---------------------------------------------------------------------------

# اعراب و علامات (Tashkeel / Harakat)
TASHKEEL_REGEX = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")

# تطویل (Kashida)
TATWEEL_REGEX = re.compile(r"\u0640")

# صفائی برائے حروفِ علت و اشکال
ALEF_VARIANTS = re.compile(r"[آأإٱ]")
YEH_VARIANTS = re.compile(r"[يىئ]")
HEH_VARIANTS = re.compile(r"[ةه]")
KAF_VARIANTS = re.compile(r"[ك]")


def normalize_urdu_text(text: str) -> str:
    """
    اردو اور عربی متن کو موازنے کے لیے معیاری بناتا ہے۔
    - اعراب ہٹاتا ہے
    - حروف کو یکساں شکل دیتا ہے
    - فالتو اسپیسز اور رموزِ اوقاف ختم کرتا ہے
    """
    if not text:
        return ""

    t = text.strip()

    # 1. اعراب اور کشیدہ کا اخراج
    t = TASHKEEL_REGEX.sub("", t)
    t = TATWEEL_REGEX.sub("", t)

    # 2. حروف کا یکسانیت لانا
    t = ALEF_VARIANTS.sub("ا", t)
    t = YEH_VARIANTS.sub("ی", t)
    t = HEH_VARIANTS.sub("ہ", t)
    t = KAF_VARIANTS.sub("ک", t)

    # 3. غیر ضروری اوقاف اور علامات کا خاتمہ
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)

    # 4. اضافی اسپیسز کو ایک اسپیس میں تبدیل کرنا
    t = re.sub(r"\s+", " ", t).strip()

    return t


def compute_content_fingerprint(text: str) -> str:
    """متن کا نارملائزڈ SHA-256 ہیش تیار کرتا ہے"""
    normalized = normalize_urdu_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def tokenize_urdu(text: str) -> Set[str]:
    """متن کو با معنی ٹوکنز (الفاظ) میں تقسیم کرتا ہے (اسٹاپ ورڈز کے بغیر)"""
    normalized = normalize_urdu_text(text)
    words = normalized.split()
    # عام بنیادی اردو اسٹاپ ورڈز جو مفہوم میں فرق نہیں ڈالتے
    stopwords = {
        "کا", "کی", "کے", "کو", "میں", "پر", "سے", "ہے", "ہیں", "تھا",
        "تھی", "تھے", "اور", "یا", "یہ", "وہ", "ان", "اس", "نے", "کہ",
        "ایک", "دو", "تین", "چار", "کیا", "کون", "کب", "کہاں", "کیوں"
    }
    return {w for w in words if len(w) > 1 and w not in stopwords}


def calculate_jaccard_similarity(text_a: str, text_b: str) -> float:
    """دو عبارتوں کے درمیان ٹوکن اوورلیپ (Jaccard Index) معلوم کرتا ہے"""
    tokens_a = tokenize_urdu(text_a)
    tokens_b = tokenize_urdu(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)

    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Result Data Class
# ---------------------------------------------------------------------------

@dataclass
class SimilarityCheckResult:
    """مشابہت و تکرار کی جانچ کا نتیجہ"""
    is_duplicate: bool
    similarity_score: float         # 0.0 تا 1.0 (1.0 = عین مطابق)
    matched_title: Optional[str] = None
    match_source: Optional[str] = None  # "exact_hash", "token_overlap", "video_history"
    explanation_urdu: str = ""


# ---------------------------------------------------------------------------
# ContentDeduplicator
# ---------------------------------------------------------------------------

class ContentDeduplicator:
    """
    نئے مجوزہ موضوعات یا کوئزز کی چینل کی سابقہ تاریخ کے ساتھ جانچ پڑتال کرتا ہے۔
    تین سطحوں پر تکرار روکتا ہے:
    1. ہو بہو SHA-256 فنگر پرنٹ
    2. پچھلی یوٹیوب ویڈیوز کے عنوانات سے مشابہت
    3. پہلے سے پوسٹ شدہ کمیونٹی کوئزز اور پولز سے مشابہت
    """

    SIMILARITY_THRESHOLD = 0.65  # 65% سے زیادہ مشابہت تکرار سمجھی جائے گی

    async def check_similarity(
        self, candidate_text: str, category: Optional[str] = None
    ) -> SimilarityCheckResult:
        """
        کسی بھی مجوزہ متن کی ڈیٹا بیس میں موجود تمام مواد سے تکرار چیک کرے۔
        """
        candidate_fp = compute_content_fingerprint(candidate_text)
        candidate_tokens = tokenize_urdu(candidate_text)

        if not candidate_tokens:
            return SimilarityCheckResult(
                is_duplicate=False,
                similarity_score=0.0,
                explanation_urdu="متن بہت مختصر ہے، جانچ ممکن نہیں"
            )

        async with AsyncSessionLocal() as session:
            # 1. پہلے سے موجود تجاویز میں ہو بہو ہیش چیک
            prop_stmt = select(ContentTopicProposal).where(
                ContentTopicProposal.content_fingerprint == candidate_fp
            )
            existing_prop = (await session.execute(prop_stmt)).scalars().first()
            if existing_prop:
                return SimilarityCheckResult(
                    is_duplicate=True,
                    similarity_score=1.0,
                    matched_title=existing_prop.topic_title_urdu,
                    match_source="exact_hash",
                    explanation_urdu=f"یہ موضوع پہلے سے موجود تجویز میں بعینہ شامل ہے: '{existing_prop.topic_title_urdu}'"
                )

            # 2. شائع شدہ یوٹیوب ویڈیوز سے مشابہت چیک
            vid_stmt = select(GrowthVideoSnapshot.title).distinct()
            videos = (await session.execute(vid_stmt)).scalars().all()
            for v_title in videos:
                v_fp = compute_content_fingerprint(v_title)
                if v_fp == candidate_fp:
                    return SimilarityCheckResult(
                        is_duplicate=True,
                        similarity_score=1.0,
                        matched_title=v_title,
                        match_source="video_history",
                        explanation_urdu=f"یہ موضوع پہلے سے یوٹیوب ویڈیو میں شائع ہو چکا ہے: '{v_title}'"
                    )

                sim = calculate_jaccard_similarity(candidate_text, v_title)
                if sim >= self.SIMILARITY_THRESHOLD:
                    return SimilarityCheckResult(
                        is_duplicate=True,
                        similarity_score=round(sim, 2),
                        matched_title=v_title,
                        match_source="token_overlap",
                        explanation_urdu=f"موجودہ یوٹیوب ویڈیو '{v_title}' سے {int(sim*100)}% مماثلت پائی گئی"
                    )

            # 3. پوسٹ قطار (PostQueue) سے کوئز/پول متن کا جائزہ
            q_stmt = select(PostQueue.question_text).limit(100)
            questions = (await session.execute(q_stmt)).scalars().all()
            for q_text in questions:
                sim = calculate_jaccard_similarity(candidate_text, q_text)
                if sim >= self.SIMILARITY_THRESHOLD:
                    return SimilarityCheckResult(
                        is_duplicate=True,
                        similarity_score=round(sim, 2),
                        matched_title=q_text[:60],
                        match_source="token_overlap",
                        explanation_urdu=f"سابقہ کمیونٹی سوال '{q_text[:40]}...' سے {int(sim*100)}% مشابہت ہے"
                    )

        # اگر کوئی تکرار نہ ملے
        return SimilarityCheckResult(
            is_duplicate=False,
            similarity_score=0.0,
            explanation_urdu="یہ منفرد موضوع ہے، سابقہ مواد سے کوئی تکرار نہیں ملی"
        )


# Singleton
content_deduplicator = ContentDeduplicator()
