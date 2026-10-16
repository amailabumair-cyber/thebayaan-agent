"""
urdu_growth_reporter.py — Phase 2: Urdu Growth Reports
=======================================================
اردو زبان میں یوٹیوب چینل 'The Bayaan' کی ترقی کی رپورٹ تیار کرتا ہے۔

اصول:
- تمام تجزیاتی متن اردو میں، اعداد/تاریخ/پاتھ انگریزی میں
- کبھی ڈیٹا من گھڑت نہ کریں
- Analytics API (watch time, CTR) کی عدم دستیابی ہمیشہ واضح کریں
- رپورٹ کا ہر حصہ ڈیٹا کے ماخذ اور حدود بیان کرے
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pytz

from .growth_comparator import growth_comparator, ComparisonReport, PeriodDelta

logger = logging.getLogger("agent_am.analytics.urdu_growth_reporter")

PKT = pytz.timezone("Asia/Karachi")
REPORTS_DIR = "reports"


class UrduGrowthReporter:
    """
    مختلف مدتوں (1، 7، 30، 90 دن) کی اردو رپورٹ تیار کرتا ہے۔
    رپورٹ Markdown فارمیٹ میں محفوظ ہوتی ہے۔
    """

    PERIOD_LABELS = {
        1: "یومیہ (1 دن)",
        7: "ہفتہ وار (7 دن)",
        30: "ماہانہ (30 دن)",
        90: "سہ ماہی (90 دن)",
    }

    async def generate_growth_report(
        self, period_days: int = 7, save_to_file: bool = True
    ) -> str:
        """
        مخصوص مدت کی اردو ترقی رپورٹ تیار کرے اور محفوظ کرے۔

        Args:
            period_days: 1، 7، 30 یا 90
            save_to_file: اگر True ہو تو reports/ فولڈر میں محفوظ کرے

        Returns:
            Markdown متن
        """
        now_pkt = datetime.now(PKT)
        today_str = now_pkt.strftime("%Y-%m-%d")
        time_str = now_pkt.strftime("%I:%M %p")

        period_label = self.PERIOD_LABELS.get(period_days, f"{period_days} دن")

        logger.info(f"اردو رپورٹ تیار ہو رہی ہے: {period_label}")

        # موازنہ رپورٹ لائیں
        comparison = await growth_comparator.compare_periods(period_days)

        # Markdown تیار کریں
        md = self._build_markdown(comparison, period_label, today_str, time_str, now_pkt)

        if save_to_file:
            path = self._save_report(md, today_str, period_days)
            logger.info(f"رپورٹ محفوظ: {path}")

        return md

    # ------------------------------------------------------------------
    # Markdown Builder
    # ------------------------------------------------------------------

    def _build_markdown(
        self,
        c: ComparisonReport,
        period_label: str,
        today_str: str,
        time_str: str,
        now_pkt: datetime,
    ) -> str:
        lines = []

        # ہیڈر
        lines += [
            f"# 📊 The Bayaan — {period_label} ترقی رپورٹ",
            f"",
            f"**تاریخ:** {today_str} | **وقت:** {time_str} (پاکستان وقت)",
            f"**چینل:** The Bayaan | **Handle:** @thebayaanurdu",
            f"",
            "---",
            "",
        ]

        # ڈیٹا کی حدود — سب سے پہلے بتائیں
        lines += [
            "## ⚠️ ڈیٹا کی دستیابی اور حدود",
            "",
            f"| میٹرک | حالت |",
            f"|-------|------|",
            f"| چینل اسنیپ شاٹس | {c.data_points_available} دنوں کا ڈیٹا موجود |",
            f"| {period_label} موازنہ | {'✅ ممکن' if c.has_sufficient_data else '⚠️ ناکافی ڈیٹا'} |",
            f"| Watch Time | ❌ دستیاب نہیں (OAuth2 درکار) |",
            f"| CTR / Impressions | ❌ دستیاب نہیں (OAuth2 درکار) |",
            f"| Average View Duration | ❌ دستیاب نہیں (OAuth2 درکار) |",
            "",
        ]

        if not c.has_sufficient_data and c.insufficient_data_reason:
            lines += [
                f"> **نوٹ:** {c.insufficient_data_reason}",
                "",
            ]

        # چینل کا جائزہ
        lines += [
            "## 📈 چینل کا جائزہ",
            "",
        ]

        if c.subscriber_delta and c.subscriber_delta.end_value is not None:
            sub_end = c.subscriber_delta.end_value
            view_end = c.view_delta.end_value if c.view_delta else "N/A"
            vid_end = c.video_count_delta.end_value if c.video_count_delta else "N/A"

            lines += [
                f"| میٹرک | موجودہ قدر | تبدیلی ({period_label}) |",
                f"|-------|-----------|----------------------|",
                self._metric_row("سبسکرائبرز", sub_end, c.subscriber_delta),
                self._metric_row("کل ویوز", view_end, c.view_delta),
                self._metric_row("ویڈیوز", vid_end, c.video_count_delta),
                "",
            ]
        else:
            lines += [
                "> ابھی چینل ڈیٹا دستیاب نہیں۔ پہلا اسنیپ شاٹ آج جمع ہو رہا ہے۔",
                "",
            ]

        # سبسکرائبر ٹرینڈ
        lines += [
            "## 👥 سبسکرائبر ٹرینڈ",
            "",
        ]
        if c.subscriber_delta and c.subscriber_delta.data_available and c.subscriber_delta.delta is not None:
            delta = c.subscriber_delta.delta
            pct = c.subscriber_delta.growth_pct
            if delta > 0:
                lines.append(f"✅ اس مدت میں **{delta:+,}** نئے سبسکرائبرز ({pct}% اضافہ)")
            elif delta < 0:
                lines.append(f"📉 اس مدت میں **{delta:,}** سبسکرائبرز کم ہوئے ({pct}% کمی)")
            else:
                lines.append("➡️ سبسکرائبرز میں کوئی تبدیلی نہیں آئی")
        else:
            lines.append("> موازنے کے لیے کم از کم 2 دن کا ڈیٹا درکار ہے۔")
        lines.append("")

        # ویوز ٹرینڈ
        lines += [
            "## 👁️ ویوز ٹرینڈ",
            "",
        ]
        if c.view_delta and c.view_delta.data_available and c.view_delta.delta is not None:
            delta = c.view_delta.delta
            pct = c.view_delta.growth_pct
            if delta > 0:
                lines.append(f"✅ **{delta:+,}** نئے ویوز ({pct}% اضافہ)")
            elif delta < 0:
                lines.append(f"📉 **{delta:,}** ویوز کم ہوئے ({pct}% کمی)")
            else:
                lines.append("➡️ ویوز میں کوئی تبدیلی نہیں")
        else:
            lines.append("> موازنے کے لیے کم از کم 2 دن کا ڈیٹا درکار ہے۔")
        lines.append("")

        # بہترین ویڈیوز
        lines += [
            "## 🌟 بہترین کارکردگی ویڈیوز",
            "",
        ]
        if c.top_performers:
            lines += [
                "| عنوان | ویوز (آج) | اضافہ |",
                "|-------|----------|-------|",
            ]
            for vp in c.top_performers:
                delta_str = f"+{vp.views_delta:,}" if vp.views_delta >= 0 else f"{vp.views_delta:,}"
                lines.append(f"| {vp.title[:60]} | {vp.views_end:,} | {delta_str} |")
            lines.append("")
        else:
            lines.append("> ویڈیو کارکردگی ڈیٹا ابھی جمع ہو رہا ہے۔")
            lines.append("")

        # کمزور ویڈیوز
        if c.declining_videos:
            lines += [
                "## 📉 کم کارکردگی ویڈیوز",
                "",
                "| عنوان | ویوز (آج) | کمی |",
                "|-------|----------|-----|",
            ]
            for vp in c.declining_videos:
                lines.append(
                    f"| {vp.title[:60]} | {vp.views_end:,} | {vp.views_delta:,} |"
                )
            lines.append("")

        # Analytics API نوٹ
        lines += [
            "## 📊 Analytics API کی حدود",
            "",
            "> **⚠️ اہم نوٹ:** YouTube Analytics API کے لیے OAuth2 user token درکار ہے۔",
            "> یہ token ابھی configure نہیں ہوا۔ اس لیے درج ذیل میٹرکس **دستیاب نہیں**:",
            ">",
            "> - Watch Time (گھنٹے)",
            "> - Average View Duration",
            "> - Impressions",
            "> - Click-Through Rate (CTR)",
            "> - Traffic Sources",
            "> - Audience Demographics",
            ">",
            "> ان میٹرکس کے لیے OAuth2 setup کریں یا YouTube Studio سے manual رپورٹ دیکھیں۔",
            "",
        ]

        # سفارشات
        lines += [
            "## 💡 سفارشات",
            "",
        ]
        recommendations = self._generate_recommendations(c)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

        # رپورٹ کا خاتمہ
        lines += [
            "---",
            "",
            f"*یہ رپورٹ Agent AM نے خودکار طریقے سے {now_pkt.strftime('%Y-%m-%d %H:%M')} (PKT) پر تیار کی۔*",
            f"*ڈیٹا ماخذ: YouTube Data API v3 (live) + local DB snapshots*",
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    def _metric_row(
        self, label: str, current_val, delta: Optional[PeriodDelta]
    ) -> str:
        """ایک میٹرک کی table row بنائے"""
        if isinstance(current_val, int):
            cur = f"{current_val:,}"
        else:
            cur = str(current_val)

        if delta and delta.data_available and delta.delta is not None:
            d = delta.delta
            pct = delta.growth_pct
            change_str = f"{d:+,}"
            if pct is not None:
                change_str += f" ({pct:+.1f}%)"
        else:
            change_str = "موازنہ ممکن نہیں (ناکافی ڈیٹا)"

        return f"| {label} | {cur} | {change_str} |"

    def _generate_recommendations(self, c: ComparisonReport) -> list:
        """رپورٹ ڈیٹا کی بنیاد پر عملی سفارشات"""
        recs = []

        if c.data_points_available < 7:
            recs.append(
                "روزانہ ڈیٹا اکٹھا جاری رکھیں — 7 دن بعد بہتر تجزیہ ممکن ہو گا۔"
            )

        if c.subscriber_delta and c.subscriber_delta.delta is not None:
            if c.subscriber_delta.delta > 0:
                recs.append("سبسکرائبرز بڑھ رہے ہیں — موجودہ کمیونٹی پوسٹنگ جاری رکھیں۔")
            elif c.subscriber_delta.delta < 0:
                recs.append(
                    "سبسکرائبرز میں کمی آئی — ویڈیو مواد اور پوسٹنگ ٹائمنگ پر نظرثانی کریں۔"
                )

        if not c.has_sufficient_data:
            recs.append(
                f"مزید {c.period_days - c.data_points_available} دن ڈیٹا جمع ہونے کا انتظار کریں "
                f"تاکہ مکمل {c.period_label} موازنہ ممکن ہو۔"
            )

        if not c.top_performers:
            recs.append(
                "ویڈیو snapshots کل سے جمع ہونا شروع ہوں گے — "
                "اگلی رپورٹ میں ویڈیو کارکردگی نظر آئے گی۔"
            )

        recs.append(
            "OAuth2 setup کریں تاکہ watch time، CTR اور audience data بھی رپورٹ میں شامل ہو۔"
        )

        if not recs:
            recs.append("ابھی کوئی خاص سفارش نہیں — سسٹم درست کام کر رہا ہے۔")

        return recs

    def _save_report(self, md: str, today_str: str, period_days: int) -> str:
        """رپورٹ فائل محفوظ کرے — موجودہ فائل کو overwrite نہ کرے"""
        os.makedirs(REPORTS_DIR, exist_ok=True)

        base = os.path.join(REPORTS_DIR, f"growth_report_{today_str}_{period_days}day.md")
        path = base
        counter = 1
        while os.path.exists(path):
            path = base.replace(".md", f"_v{counter}.md")
            counter += 1

        with open(path, "w", encoding="utf-8") as f:
            f.write(md)

        return path

    async def generate_all_reports(self) -> dict:
        """
        تمام مدتوں (1، 7، 30، 90 دن) کی رپورٹ بیک وقت تیار کرے۔
        """
        results = {}
        for days in [1, 7, 30, 90]:
            try:
                await self.generate_growth_report(period_days=days)
                results[f"{days}day"] = "✅ تیار"
            except Exception as e:
                results[f"{days}day"] = f"❌ خرابی: {e}"
                logger.exception(f"{days}-دن رپورٹ میں خرابی: {e}")
        return results


# Singleton
urdu_growth_reporter = UrduGrowthReporter()
