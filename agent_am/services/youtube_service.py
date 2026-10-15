import logging
from typing import Dict, Any, List, Optional
import httpx
from agent_am.config.settings import settings

logger = logging.getLogger("agent_am.youtube_service")

class YouTubeService:
    """
    YouTube Data API v3 انضمام برائے 'The Bayan'
    چینل کی تفصیلات، ویڈیوز کی کارکردگی اور اینالیٹکس شماریات حاصل کرتا ہے۔
    """

    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY.strip()
        self.channel_id = settings.CHANNEL_ID.strip()
        self.channel_name = settings.CHANNEL_NAME.strip()
        self.base_url = "https://www.googleapis.com/youtube/v3"

    def is_configured(self) -> bool:
        """چیک کرتا ہے کہ آیا یوٹیوب ڈیٹا اے پی آئی چابی موجود ہے"""
        return bool(self.api_key)

    async def find_channel_by_name(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """چینل کے نام سے سرچ کر کے متعلقہ چینل کی معلومات حاصل کرتا ہے"""
        if not self.is_configured():
            logger.warning("YouTube API Key موجود نہیں ہے۔ فرضی ڈیٹا کا استعمال کیا جا رہا ہے۔")
            return self._get_mock_channel(channel_name)

        url = f"{self.base_url}/search"
        params = {
            "key": self.api_key,
            "q": channel_name,
            "type": "channel",
            "part": "snippet",
            "maxResults": 1
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return None
            channel_id = items[0]["snippet"]["channelId"]
            return await self.get_channel_details(channel_id)

    async def get_channel_details(self, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """چینل کی تفصیلی شماریات (سبسکرائبرز، ویوز، ویڈیوز) حاصل کرتا ہے"""
        target_id = channel_id or self.channel_id
        if not self.is_configured() or not target_id:
            return self._get_mock_channel(self.channel_name)

        url = f"{self.base_url}/channels"
        params = {
            "key": self.api_key,
            "id": target_id,
            "part": "snippet,statistics,contentDetails"
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    return self._get_mock_channel(self.channel_name)
                
                ch = items[0]
                snippet = ch.get("snippet", {})
                stats = ch.get("statistics", {})
                content = ch.get("contentDetails", {})
                uploads_playlist = content.get("relatedPlaylists", {}).get("uploads", "")

                return {
                    "channel_id": ch["id"],
                    "title": snippet.get("title", self.channel_name),
                    "description": snippet.get("description", ""),
                    "custom_url": snippet.get("customUrl", ""),
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "views": int(stats.get("viewCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                    "uploads_playlist_id": uploads_playlist,
                    "is_live_data": True
                }
        except Exception as e:
            logger.error(f"YouTube Channel Details حاصل کرنے میں خرابی: {str(e)}")
            return self._get_mock_channel(self.channel_name)

    async def get_recent_videos(self, channel_id: Optional[str] = None, max_results: int = 15) -> List[Dict[str, Any]]:
        """چینل کی تازہ ترین ویڈیوز کی لسٹ اور ان کے ویوز و کمنٹس حاصل کرتا ہے"""
        if not self.is_configured():
            return self._get_mock_videos()

        ch_data = await self.get_channel_details(channel_id)
        uploads_id = ch_data.get("uploads_playlist_id")
        
        if not uploads_id:
            # فال بیک: اگر چینل آئی ڈی سے uploads پلے لسٹ معلوم کی جائے
            ch_id = channel_id or self.channel_id
            if ch_id and len(ch_id) > 2 and ch_id.startswith("UC"):
                uploads_id = "UU" + ch_id[2:]

        if not uploads_id:
            return self._get_mock_videos()

        try:
            # 1. پلے لسٹ سے ویڈیوز کی آئی ڈیز حاصل کریں
            url = f"{self.base_url}/playlistItems"
            params = {
                "key": self.api_key,
                "playlistId": uploads_id,
                "part": "snippet,contentDetails",
                "maxResults": max_results
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                video_items = data.get("items", [])
                
                if not video_items:
                    return self._get_mock_videos()

                video_ids = [item["contentDetails"]["videoId"] for item in video_items if "contentDetails" in item]
                
                # 2. ویڈیوز کے تازہ ترین اینالیٹکس لائیں
                return await self.get_videos_metrics(video_ids)
        except Exception as e:
            logger.error(f"ویڈیوز لانے میں خرابی: {str(e)}")
            return self._get_mock_videos()

    async def get_videos_metrics(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """ویڈیوز کی انفرادی شماریات (ویوز، لائیکس، کمنٹس) لاتا ہے"""
        if not video_ids:
            return []

        url = f"{self.base_url}/videos"
        params = {
            "key": self.api_key,
            "id": ",".join(video_ids),
            "part": "snippet,statistics,contentDetails"
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    stats = item.get("statistics", {})
                    results.append({
                        "video_id": item["id"],
                        "title": snippet.get("title", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "duration": item.get("contentDetails", {}).get("duration", "")
                    })
                return results
        except Exception as e:
            logger.error(f"ویڈیو میٹرکس لانے میں خرابی: {str(e)}")
            return []

    # =========================================================================
    # آف لائن / ٹیسٹنگ ماک ڈیٹا (Mock Data for Testing & Setup)
    # =========================================================================

    def _get_mock_channel(self, name: str) -> Dict[str, Any]:
        return {
            "channel_id": "UC_TheBayan_DemoChannel",
            "title": name or "The Bayan",
            "description": "The Bayan - مستند اسلامی تاریخ، خلافت راشدہ اور سیرت النبی ﷺ پر مبنی علمی ویڈیوز",
            "custom_url": "@TheBayanOfficial",
            "subscribers": 48500,
            "views": 3250000,
            "video_count": 86,
            "uploads_playlist_id": "UU_TheBayan_Uploads",
            "is_live_data": False
        }

    def _get_mock_videos(self) -> List[Dict[str, Any]]:
        return [
            {
                "video_id": "vid_bayan_001",
                "title": "غزوہ تبوک اور منافقین کا کردار | The Bayaan تاریخ اسلام",
                "published_at": "2026-10-10T14:00:00Z",
                "views": 45200,
                "likes": 3800,
                "comments": 420,
                "duration": "PT18M24S"
            },
            {
                "video_id": "vid_bayan_002",
                "title": "امیر المؤمنین حضرت عمر فاروق رضی اللہ عنہ کا عدالتی نظام",
                "published_at": "2026-10-06T15:00:00Z",
                "views": 68900,
                "likes": 5600,
                "comments": 710,
                "duration": "PT24M10S"
            },
            {
                "video_id": "vid_bayan_003",
                "title": "مسلم سپین (اندلس) کا عروج و زوال - ایک بصیرت افروز تجزیہ",
                "published_at": "2026-09-28T16:00:00Z",
                "views": 94300,
                "likes": 8100,
                "comments": 1150,
                "duration": "PT32M15S"
            },
            {
                "video_id": "vid_bayan_004",
                "title": "بیت الحکمہ بغداد اور مسلم سائنسی انقلاب",
                "published_at": "2026-09-20T12:00:00Z",
                "views": 31400,
                "likes": 2400,
                "comments": 290,
                "duration": "PT15M40S"
            }
        ]

youtube_service = YouTubeService()
