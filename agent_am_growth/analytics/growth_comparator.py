"""
growth_comparator.py — Phase 2: Period-over-Period Growth Analysis
==================================================================
مختلف مدتوں (1، 7، 30، 90 دن) کا تقابلی تجزیہ۔

اہم اصول:
- اگر کافی تاریخی ڈیٹا نہ ہو تو واضح طور پر "ناکافی ڈیٹا" بتائیں
- کبھی ڈیٹا اخذ نہ کریں یا اندازوں کو حقیقت نہ بتائیں
- ہر نتیجے میں ڈیٹا کی دستیابی کی حد واضح کریں
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import pytz

from .metrics_collector import (
    metrics_collector,
    ChannelSnapshot,
    VideoMetricSnapshot,
)

logger = logging.getLogger("agent_am.analytics.growth_comparator")

PKT = pytz.timezone("Asia/Karachi")


# ---------------------------------------------------------------------------
# Result Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PeriodDelta:
    """دو مدتوں کے درمیان فرق"""
    metric_name: str
    start_value: Optional[int]
    end_value: Optional[int]
    delta: Optional[int]           # فرق (مثبت یا منفی)
    growth_pct: Optional[float]    # فیصد اضافہ یا کمی
    data_available: bool = True
    note: str = ""


@dataclass
class VideoPerformance:
    """ایک ویڈیو کی مخصوص مدت میں کارکردگی"""
    video_id: str
    title: str
    views_start: int
    views_end: int
    views_delta: int
    likes_delta: int
    comments_delta: int


@dataclass
class ComparisonReport:
    """مقابلاتی تجزیے کا مکمل نتیجہ"""
    period_days: int
    period_label: str              # "7 دن" / "30 دن" وغیرہ
    start_date: Optional[str]      # YYYY-MM-DD
    end_date: str                  # YYYY-MM-DD (آج)
    data_points_available: int     # DB میں اصل ریکارڈز کی تعداد
    has_sufficient_data: bool      # کیا موازنہ ممکن ہے؟
    insufficient_data_reason: str  # اگر ناکافی ہے تو کیوں

    subscriber_delta: Optional[PeriodDelta] = None
    view_delta: Optional[PeriodDelta] = None
    video_count_delta: Optional[PeriodDelta] = None

    top_performers: List[VideoPerformance] = field(default_factory=list)
    declining_videos: List[VideoPerformance] = field(default_factory=list)

    analytics_api_note: str = (
        "⚠️ Analytics API (watch time, CTR, impressions): OAuth2 token "
        "configure نہیں — یہ میٹرکس دستیاب نہیں"
    )


# ---------------------------------------------------------------------------
# GrowthComparator
# ---------------------------------------------------------------------------

class GrowthComparator:
    """
    چینل کی مختلف مدتوں میں ترقی کا موازنہ کرتا ہے۔
    صرف وہ ڈیٹا استعمال کرتا ہے جو DB میں واقعی موجود ہو۔
    """

    PERIOD_LABELS = {
        1: "1 دن",
        7: "7 دن",
        30: "30 دن",
        90: "90 دن",
    }

    async def compare_periods(self, period_days: int) -> ComparisonReport:
        """
        آج اور N دن پہلے کے درمیان موازنہ کرے۔

        Args:
            period_days: 1، 7، 30 یا 90

        Returns:
            ComparisonReport — اگر ڈیٹا ناکافی ہو تو
            has_sufficient_data=False اور وجہ لکھی ہوئی ہو گی
        """
        today_str = datetime.now(PKT).strftime("%Y-%m-%d")
        period_label = self.PERIOD_LABELS.get(period_days, f"{period_days} دن")

        # پہلے دیکھیں کتنا ڈیٹا موجود ہے
        available_count = await metrics_collector.get_available_dates_count()

        base_report = ComparisonReport(
            period_days=period_days,
            period_label=period_label,
            start_date=None,
            end_date=today_str,
            data_points_available=available_count,
            has_sufficient_data=False,
            insufficient_data_reason="",
        )

        # چینل اسنیپ شاٹس لائیں
        snapshots = await metrics_collector.get_historical_channel_snapshots(
            days=max(period_days + 2, 92)  # تھوڑا extra margin
        )

        if available_count == 0:
            base_report.insufficient_data_reason = (
                f"DB میں ابھی کوئی چینل اسنیپ شاٹ موجود نہیں۔ "
                f"روزانہ 9:30 بجے ڈیٹا اکٹھا ہو گا۔ "
                f"پہلا موازنہ {period_days} دن بعد ممکن ہو گا۔"
            )
            return base_report

        if available_count == 1:
            # صرف ایک دن کا ڈیٹا — مقابلہ ممکن نہیں
            base_report.insufficient_data_reason = (
                f"صرف 1 دن کا ڈیٹا موجود ہے۔ "
                f"{period_days}-دن موازنے کے لیے کم از کم 2 الگ دنوں کا ڈیٹا چاہیے۔"
            )
            # پھر بھی آج کی baseline معلومات دیں
            latest = snapshots[-1]
            base_report.subscriber_delta = PeriodDelta(
                metric_name="subscribers",
                start_value=None,
                end_value=latest.subscribers,
                delta=None,
                growth_pct=None,
                data_available=False,
                note=f"صرف آج کا ڈیٹا: {latest.subscribers} subscribers",
            )
            base_report.view_delta = PeriodDelta(
                metric_name="total_views",
                start_value=None,
                end_value=latest.total_views,
                delta=None,
                growth_pct=None,
                data_available=False,
                note=f"صرف آج کا ڈیٹا: {latest.total_views} views",
            )
            base_report.video_count_delta = PeriodDelta(
                metric_name="video_count",
                start_value=None,
                end_value=latest.video_count,
                delta=None,
                growth_pct=None,
                data_available=False,
                note=f"صرف آج کا ڈیٹا: {latest.video_count} videos",
            )
            return base_report


        # کافی ڈیٹا ہو تو موازنہ کریں
        # سب سے پرانا اور سب سے نیا اسنیپ شاٹ نکالیں
        oldest = snapshots[0]
        latest = snapshots[-1]

        # چیک کریں کیا یہ واقعی period_days کا موازنہ ممکن ہے
        actual_span = self._date_diff(oldest.snapshot_date, latest.snapshot_date)

        if actual_span < period_days:
            base_report.insufficient_data_reason = (
                f"صرف {actual_span} دن کا ڈیٹا موجود ہے ({available_count} اسنیپ شاٹس)۔ "
                f"{period_days}-دن موازنے کے لیے {period_days} دن کا ڈیٹا چاہیے۔ "
                f"ابھی {actual_span}-دن موازنہ دکھایا جا رہا ہے (جو دستیاب ہے)۔"
            )
            # Partial موازنہ — جو ملا وہ دکھائیں لیکن واضح کریں
            start_snap = oldest
        else:
            base_report.has_sufficient_data = True
            # period_days پہلے کا اسنیپ شاٹ تلاش کریں
            target_date = (
                datetime.now(PKT) - timedelta(days=period_days)
            ).strftime("%Y-%m-%d")
            start_snap = self._find_closest_snapshot(snapshots, target_date)
            if not start_snap:
                start_snap = oldest

        base_report.start_date = start_snap.snapshot_date

        # ڈیلٹا حساب کریں
        base_report.subscriber_delta = self._calc_delta(
            "subscribers", start_snap.subscribers, latest.subscribers
        )
        base_report.view_delta = self._calc_delta(
            "total_views", start_snap.total_views, latest.total_views
        )
        base_report.video_count_delta = self._calc_delta(
            "video_count", start_snap.video_count, latest.video_count
        )

        # ویڈیو کارکردگی
        top, declining = await self._analyze_video_performance(
            period_days=max(actual_span, 1)
        )
        base_report.top_performers = top
        base_report.declining_videos = declining

        return base_report

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    def _calc_delta(
        self, name: str, start_val: int, end_val: int
    ) -> PeriodDelta:
        delta = end_val - start_val
        pct = round((delta / start_val * 100), 2) if start_val > 0 else None
        return PeriodDelta(
            metric_name=name,
            start_value=start_val,
            end_value=end_val,
            delta=delta,
            growth_pct=pct,
            data_available=True,
        )

    def _find_closest_snapshot(
        self,
        snapshots: List[ChannelSnapshot],
        target_date: str,
    ) -> Optional[ChannelSnapshot]:
        """target_date کے سب سے قریب ترین اسنیپ شاٹ نکالے"""
        best = None
        best_diff = None
        for s in snapshots:
            diff = abs(self._date_diff(s.snapshot_date, target_date))
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best = s
        return best

    @staticmethod
    def _date_diff(date_a: str, date_b: str) -> int:
        """دو YYYY-MM-DD تاریخوں کا فرق دنوں میں"""
        try:
            a = datetime.strptime(date_a, "%Y-%m-%d")
            b = datetime.strptime(date_b, "%Y-%m-%d")
            return abs((b - a).days)
        except ValueError:
            return 0

    async def _analyze_video_performance(
        self, period_days: int
    ) -> tuple[List[VideoPerformance], List[VideoPerformance]]:
        """
        ویڈیوز کو views delta کے مطابق ترتیب دے۔
        اگر صرف ایک دن کا ڈیٹا ہو تو مطلق views سے ترتیب دیں۔
        """
        snapshots = await metrics_collector.get_historical_video_snapshots(
            days=period_days + 2
        )
        if not snapshots:
            return [], []

        # video_id کے مطابق گروپ کریں
        by_video: Dict[str, List[VideoMetricSnapshot]] = {}
        for s in snapshots:
            by_video.setdefault(s.video_id, []).append(s)

        performances = []
        for vid_id, snaps in by_video.items():
            snaps.sort(key=lambda x: x.snapshot_date)
            first = snaps[0]
            last = snaps[-1]

            vp = VideoPerformance(
                video_id=vid_id,
                title=last.title,
                views_start=first.views,
                views_end=last.views,
                views_delta=last.views - first.views,
                likes_delta=last.likes - first.likes,
                comments_delta=last.comments - first.comments,
            )
            performances.append(vp)

        # views_delta کے مطابق ترتیب دیں
        performances.sort(key=lambda x: x.views_delta, reverse=True)

        top = performances[:5]
        declining = [p for p in performances if p.views_delta < 0][:5]

        return top, declining

    async def quick_summary(self) -> Dict[str, Any]:
        """
        سب سے حالیہ چینل ڈیٹا کا مختصر خلاصہ — dashboard کے لیے
        """
        snapshots = await metrics_collector.get_historical_channel_snapshots(days=2)
        if not snapshots:
            return {
                "available": False,
                "reason": "ابھی کوئی ڈیٹا جمع نہیں ہوا",
            }
        latest = snapshots[-1]
        return {
            "available": True,
            "date": latest.snapshot_date,
            "subscribers": latest.subscribers,
            "total_views": latest.total_views,
            "video_count": latest.video_count,
            "data_source": latest.data_source,
            "analytics_api": "دستیاب نہیں — OAuth2 درکار",
        }


# Singleton
growth_comparator = GrowthComparator()
