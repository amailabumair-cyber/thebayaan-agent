import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from agent_am.config.settings import settings

logger = logging.getLogger("agent_am.ai_engine")

class AIEngine:
    """
    Agent AM کا مرکزی اے آئی ریزننگ اور کنٹینٹ انجن
    اسلامی تاریخ اور چینل کے موضوعات پر مستند کوئز اور ٹیکسٹ پولز تیار کرتا ہے۔
    گوگل جیمنائی (Gemini) اور اوپن اے آئی (ChatGPT) دونوں کو سپورٹ کرتا ہے۔
    """

    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self.gemini_key = settings.GEMINI_API_KEY.strip()
        self.openai_key = settings.OPENAI_API_KEY.strip()
        self.model_name = settings.AI_MODEL_NAME.strip()

    def compute_content_hash(self, question: str, options: List[str] = None) -> str:
        """سوال اور آپشنز سے منفرد SHA256 ہیش بناتا ہے تاکہ ڈپلیکیٹ روکا جا سکے"""
        normalized = question.strip().lower()
        if options:
            normalized += "_" + "_".join(sorted([opt.strip().lower() for opt in options]))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def _call_gemini(self, system_instruction: str, prompt: str) -> str:
        """گوگل جیمنائی اے پی آئی کو براہِ راست ہائپر-فاسٹ کال کرتا ہے"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}
            ],
            "generationConfig": {
                "temperature": 0.4,
                "responseMimeType": "application/json"
            }
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_openai(self, system_instruction: str, prompt: str) -> str:
        """اوپن اے آئی (ChatGPT) اے پی آئی کو کال کرتا ہے"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name if "gpt" in self.model_name else "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _query_llm(self, system_instruction: str, prompt: str) -> str:
        """کنفیگرڈ ماڈل کے مطابق ایل ایل ایم کال کو ہینڈل کرتا ہے"""
        if self.provider == "gemini" and self.gemini_key:
            return await self._call_gemini(system_instruction, prompt)
        elif self.provider == "openai" and self.openai_key:
            return await self._call_openai(system_instruction, prompt)
        else:
            raise ValueError("کوئی فعال AI API Key موجود نہیں ہے۔ براۂ مہربانی .env میں چابی درج کریں۔")

    async def generate_quiz(self, recent_topics: List[str] = None, target_topic: Optional[str] = None) -> Dict[str, Any]:
        """
        اسلامی تاریخ پر مبنی معتبر کوئز (Quiz) تیار کرتا ہے (کسی خاص موضوع یا عمومی)
        """
        topics_str = ", ".join(recent_topics) if recent_topics else "کوئی نہیں"
        target_clause = f"خاص مطلوبہ موضوع جس پر سوال بنانا لازمی ہے: '{target_topic}'" if target_topic else "موضوع کا انتخاب اسلامی تاریخ کے معتبر واقعات میں سے کریں"

        system_instruction = (
            "آپ یوٹیوب چینل 'The Bayan' کے سینئر اسلامی مورخ اور ریسرچر ہیں۔ "
            "آپ کا کام اسلامی تاریخ، خلافت راشدہ، صحابہ کرام رضی اللہ عنہم، اور اموی و عباسی ادوار پر مبنی "
            "ایک انتہائی مستند، دلچسپ اور علمی کوئز (Quiz) سوال تیار کرنا ہے۔ "
            "ہر سوال کا جواب 100% معتبر تاریخی ماخذ (جیسے تاریخ طبری، البدایہ والنہایہ، سیرت ابن ہشام) سے تصدیق شدہ ہونا چاہیے۔ "
            "سنسنی خیز یا ضعیف روایات سے مکمل اجتناب کریں۔ "
            "زبان خالص اور شستہ اردو ہونی چاہیے۔ جواب صرف JSON فارمیٹ میں دیں۔"
        )
        prompt = f"""
ایک نیا اسلامی تاریخ کوئز تیار کریں۔
{target_clause}
حالیہ موضوعات جو دہرائے نہیں جانے چاہئیں: {topics_str}

آپ کو درج ذیل JSON فارمیٹ میں آؤٹ پٹ دینا ہوگا:
{{
    "question": "سوال اردو میں",
    "options": ["آپشن 1", "آپشن 2", "آپشن 3", "آپشن 4"],
    "correct_answer": "درست آپشن کا متن",
    "explanation": "درست جواب کی مختصر و جامع علمی وضاحت",
    "source_reference": "معتبر تاریخی حوالہ و کتاب کا نام (مثلاً البدایہ والنہایہ، جلد دوم)",
    "topic": "موضوع کا مختصر عنوان"
}}
"""
        try:
            raw_json = await self._query_llm(system_instruction, prompt)
            quiz_data = json.loads(raw_json)
            # تصدیق و توثیق
            self.verify_quiz_structure(quiz_data)
            quiz_data["content_hash"] = self.compute_content_hash(quiz_data["question"], quiz_data["options"])
            return quiz_data
        except Exception as e:
            logger.warning(f"AI API دستیاب نہیں یا ایرر آیا: {str(e)}۔ معتبر فال بیک کوئز استعمال کیا جا رہا ہے۔")
            return self._get_verified_fallback_quiz(recent_topics, target_topic)

    async def generate_poll(self, recent_topics: List[str] = None, target_topic: Optional[str] = None) -> Dict[str, Any]:
        """
        دلچسپ اور فکری ٹیکسٹ پول (Text Poll) تیار کرتا ہے
        """
        topics_str = ", ".join(recent_topics) if recent_topics else "کوئی نہیں"
        target_clause = f"خاص مطلوبہ موضوع: '{target_topic}'" if target_topic else "موضوع کا انتخاب اسلامی تاریخ کے معتبر ادوار میں سے کریں"

        system_instruction = (
            "آپ 'The Bayan' چینل کے کنٹینٹ اسٹریٹیجسٹ ہیں۔ "
            "آپ کو یوٹیوب کمیونٹی ٹیب کے لیے ایک مثبت، تعلیمی اور فکری ٹیکسٹ پول (Text Poll) تیار کرنا ہے۔ "
            "پول کا مقصد ناظرین کی رائے اور دلچسپی جاننا ہے، نہ کہ متنازعہ یا مسلکی بحث چھیڑنا۔ "
            "زبان شستہ اردو ہو اور جواب صرف JSON میں ہو۔"
        )
        prompt = f"""
ایک نیا اردو ٹیکسٹ پول تیار کریں۔
{target_clause}
حالیہ موضوعات: {topics_str}

درج ذیل JSON فارمیٹ لازمی ہے:
{{
    "question": "پول کا سوال اردو میں",
    "options": ["آپشن 1", "آپشن 2", "آپشن 3", "آپشن 4"],
    "explanation": "اس پول کا پس منظر یا علمی مقصد",
    "source_reference": "تاریخی پس منظر یا موضوع",
    "topic": "عنوان"
}}
"""
        try:
            raw_json = await self._query_llm(system_instruction, prompt)
            poll_data = json.loads(raw_json)
            self.verify_poll_structure(poll_data)
            poll_data["content_hash"] = self.compute_content_hash(poll_data["question"], poll_data["options"])
            return poll_data
        except Exception as e:
            logger.warning(f"AI API دستیاب نہیں یا ایرر آیا: {str(e)}۔ فال بیک پول استعمال کیا جا رہا ہے۔")
            return self._get_verified_fallback_poll(recent_topics, target_topic)

    async def generate_image_post(self, recent_topics: List[str] = None, target_topic: Optional[str] = None) -> Dict[str, Any]:
        """
        تصویر پوسٹ کے لیے مستند تاریخی یا قرآنی اقتباس مع 1080x1080 نفیس کارڈ تیار کرتا ہے
        جیمنائی اے آئی کے ذریعے تاریخی اور اسلامی صحت کی مکمل توثیق کے ساتھ
        """
        from agent_am.services.islamic_catalog import find_image_post_by_topic
        from agent_am.services.image_card_service import image_card_service

        system_instruction = (
            "آپ یوٹیوب چینل 'The Bayaan' (دی بیان) کے لیے مستند اسلامی تاریخ، سیرت اور قرآنی علوم کے ماہر محقق ہیں۔ "
            "آپ کو دیے گئے موضوع پر انتہائی پر اثر، دلنشین، اور 100% تاریخی و دینی لحاظ سے درست پیغام یا عبرت کا درس تیار کرنا ہے۔\n\n"
            "سخت تاریخی و شرعی ضوابط:\n"
            "1. اگر موضوع فرعون، نمرود، قارون، ابو جہل یا کوئی ظالم/سرکش کردار ہو: تو ہرگز ہرگز ان کی طرف 'اخلاص'، 'ثابت قدمی' یا کوئی فضیلت منسوب نہ کی جائے! "
            "بلکہ ان کا تذکرہ تکبر کے عبرتناک انجام، غرور کی شکست، اور اللہ کے عذاب و غرقابی کے درس کے طور پر ہو۔ حوالہ قرآن کی متعلقہ آیت کا ہو۔\n"
            "2. اگر موضوع کوئی نبی، صحابی یا نیک ہستی ہو (جیسے موسیٰؑ، ابراہیمؑ، عمر فاروقؓ): تو ان کے توکل، صبر، عدل، استقامت اور سیرت کا نورانی پہلو بیان کیا جائے۔\n"
            "3. عنوان پر وقار ہو (1 لائن)۔ کارڈ کا متن فصیح اور بامحاورہ اردو ہو (2 سے 3 جملے)۔\n"
            "4. حوالہ لازمی اور قطعی مستند ہو (سورہ و آیت نمبر، یا صحیح حدیث، یا البدایہ والنہایہ)۔"
        )
        prompt = f"""
مطلوبہ موضوع: {target_topic or 'اسلامی تاریخ و عبرت'}

براہِ کرم درج ذیل JSON فارمیٹ میں جواب فراہم کریں:
{{
    "title": "عنوان (مثلاً: عبرت کا درس: فرعون کا انجام یا حضرت موسیٰؑ کا توکل)",
    "card_text": "کارڈ پر لکھا جانے والا پر اثر اردو متن",
    "source_reference": "مستند ماخذ و حوالہ (مثلاً: قرآن مجید، سورہ یونس: 92)",
    "caption": "یوٹیوب کمیونٹی پوسٹ کا تفصیلی کیپشن مع ہیش ٹیگز"
}}
"""
        base_data = None
        try:
            raw_json = await self._query_llm(system_instruction, prompt)
            ai_data = json.loads(raw_json)
            if ai_data.get("card_text") and ai_data.get("title"):
                base_data = {
                    "topic": target_topic or "اسلامی تاریخ",
                    "title": ai_data.get("title"),
                    "card_text": ai_data.get("card_text"),
                    "source_reference": ai_data.get("source_reference", "دی بیان (The Bayaan)"),
                    "question": ai_data.get("caption") or (
                        f"🕌 {ai_data.get('title')}\n\n"
                        f"\"{ai_data.get('card_text')}\"\n\n"
                        f"📖 ماخذ و حوالہ: {ai_data.get('source_reference')}\n\n"
                        f"— پیشکش: دی بیان (The Bayaan)\n#TheBayaan #IslamicHistory"
                    ),
                    "content_hash": hashlib.sha256(f"{ai_data.get('title')}_{ai_data.get('card_text')}".encode("utf-8")).hexdigest()
                }
        except Exception as e:
            logger.warning(f"AI اقتباس جنریشن میں تنبیہ: {e}، کیٹلاگ فال بیک استعمال ہو رہا ہے")

        if not base_data:
            base_data = find_image_post_by_topic(target_topic)

        card_path = await image_card_service.generate_image_post_card_async(
            title=base_data.get("title", ""),
            content_text=base_data.get("card_text", ""),
            source=base_data.get("source_reference", "دی بیان (The Bayaan)")
        )
        base_data["image_path"] = str(card_path)
        base_data["post_type"] = "IMAGE"
        return base_data

    async def generate_image_poll(self, recent_topics: List[str] = None, target_topic: Optional[str] = None) -> Dict[str, Any]:
        """
        تصویر پول (Image Poll) کے لیے سوال مع 2 تا 4 آپشنز اور ان کے انفرادی اسکوائر کارڈز تیار کرتا ہے
        """
        from agent_am.services.islamic_catalog import find_image_poll_by_topic
        from agent_am.services.image_card_service import image_card_service

        base_data = find_image_poll_by_topic(target_topic)
        options = base_data.get("options", [])
        option_images = []
        for idx, opt_text in enumerate(options, 1):
            opt_card = image_card_service.generate_poll_option_card(
                option_index=idx,
                option_text=opt_text
            )
            option_images.append(str(opt_card))

        base_data["option_images"] = option_images
        base_data["post_type"] = "IMAGE_POLL"
        return base_data


    def verify_quiz_structure(self, data: Dict[str, Any]) -> None:
        """کوئز کے بنیادی اسٹرکچر اور درست جواب کی جانچ"""
        if not data.get("question"):
            raise ValueError("کوئز کا سوال خالی ہے")
        options = data.get("options", [])
        if len(options) < 2 or len(options) > 5:
            raise ValueError("کوئز میں 2 سے 4 آپشنز ہونا ضروری ہیں")
        correct = data.get("correct_answer")
        if not correct or correct not in options:
            raise ValueError("درست جواب (correct_answer) فراہم کردہ آپشنز کی فہرست میں موجود نہیں ہے")

    def verify_poll_structure(self, data: Dict[str, Any]) -> None:
        """ٹیکسٹ پول کے اسٹرکچر کی جانچ"""
        if not data.get("question"):
            raise ValueError("پول کا سوال خالی ہے")
        options = data.get("options", [])
        if len(options) < 2 or len(options) > 5:
            raise ValueError("پول میں کم از کم 2 آپشنز درکار ہیں")

    async def analyze_channel_data(self, channel_stats: Dict[str, Any], videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        چینل کے ڈیٹا کا جامع تجزیہ کرتا ہے اور اردو تجاویز مرتب کرتا ہے
        """
        system_instruction = (
            "آپ یوٹیوب گروتھ اور ڈیٹا اینالیٹکس کے ماہر ہیں۔ "
            "آپ کو 'The Bayan' چینل کے تازہ ترین ڈیٹا کا تجزیہ کر کے اردو میں پیشہ ورانہ اور قابل عمل تجاویز تیار کرنی ہیں۔"
        )
        prompt = f"""
چینل شماریات:
{json.dumps(channel_stats, ensure_ascii=False, indent=2)}

حالیہ ویڈیوز کی کارکردگی:
{json.dumps(videos[:10], ensure_ascii=False, indent=2)}

براہِ کرم درج ذیل فارمیٹ میں JSON تجزیہ فراہم کریں:
{{
    "summary_urdu": "چینل کی مجموعی صورتحال کا جامع خلاصہ",
    "top_performing_observations": ["مشاہدہ 1", "مشاہدہ 2"],
    "underperforming_observations": ["بہتری کی گنجائش 1", "بہتری کی گنجائش 2"],
    "recommendations": ["ٹھوس تجویز 1", "ٹھوس تجویز 2", "ٹھوس تجویز 3"],
    "future_topics": ["مستقبل کا مجوزہ موضوع 1", "مستقبل کا مجوزہ موضوع 2"]
}}
"""
        try:
            raw_json = await self._query_llm(system_instruction, prompt)
            return json.loads(raw_json)
        except Exception as e:
            logger.warning(f"تجزیاتی AI ماڈل دستیاب نہیں: {str(e)}۔ معیاری آڈٹ تجزیہ کیا جا رہا ہے۔")
            return self._get_fallback_analysis(channel_stats, videos)

    # =========================================================================
    # فال بیک ڈیٹا سیٹ (Verified Fallback Datasets for High Availability)
    # جب نیٹ ورک یا API کی دستیاب نہ ہو تو سسٹم بند نہیں ہوگا بلکہ معتبر ذخیرے سے کام لے گا
    # =========================================================================

    def _get_verified_fallback_quiz(self, recent_topics: List[str] = None, target_topic: Optional[str] = None) -> Dict[str, Any]:
        from agent_am.services.islamic_catalog import find_quiz_by_topic, ALL_QUIZ_CATALOG

        if target_topic:
            match = find_quiz_by_topic(target_topic)
            if match:
                return match

        # ورنہ حالیہ موضوعات کو مدنظر رکھ کر انتخاب کریں
        for item in ALL_QUIZ_CATALOG:
            if not recent_topics or item["topic"] not in recent_topics:
                res = dict(item)
                res["content_hash"] = self.compute_content_hash(res["question"], res["options"])
                return res

        res = dict(ALL_QUIZ_CATALOG[0])
        res["content_hash"] = self.compute_content_hash(res["question"], res["options"])
        return res

    def _get_verified_fallback_poll(self, recent_topics: List[str] = None, target_topic: Optional[str] = None) -> Dict[str, Any]:
        from agent_am.services.islamic_catalog import find_poll_by_topic, ALL_QUIZ_CATALOG

        if target_topic:
            return find_poll_by_topic(target_topic)

        # ورنہ کیٹلاگ سے منتخب کریں
        for item in ALL_QUIZ_CATALOG:
            if not recent_topics or item["topic"] not in recent_topics:
                return find_poll_by_topic(item["topic"])

        return find_poll_by_topic(ALL_QUIZ_CATALOG[0]["topic"])


    def _get_fallback_analysis(self, channel_stats: Dict[str, Any], videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_vids = len(videos)
        views = channel_stats.get("views", 0)
        return {
            "summary_urdu": f"چینل 'The Bayan' کے پاس اس وقت {total_vids} دستیاب ویڈیوز اور مجموعی طور پر {views:,} مشاہدات (Views) ہیں۔ چینل کی بنیادی سمت اسلامی تاریخ اور معلوماتی مواد پر مستحکم ہے۔",
            "top_performing_observations": [
                "تاریخی اور سیرت کے موضوعات پر مبنی ویڈیوز پر سامعین کا مثبت ردعمل ہے",
                "معلوماتی تھمب نیلز اور تاریخی عنوانات زیادہ کلکس حاصل کر رہے ہیں"
            ],
            "underperforming_observations": [
                "پرانی ویڈیوز پر سامعین کے تعامل (Engagement) میں بتدریج کمی دیکھی گئی ہے",
                "یوٹیوب کمیونٹی ٹیب پر روزانہ کی بنیاد پر باقاعدہ کوئز اور پولز سے چینل کی ریچ دگنی ہو سکتی ہے"
            ],
            "recommendations": [
                "شام 6:00 سے 9:00 بجے کے دوران روزانہ کمیونٹی کوئز اور ٹیکسٹ پول شیڈول کریں",
                "سب سے زیادہ دیکھی جانے والی ویڈیوز کے موضوعات پر مبنی ضمنی سوالات تیار کریں",
                "سامعین سے ان کی پسندیدہ کتب و تاریخی واقعات کے بارے میں پولز کے ذریعے رائے طلب کریں"
            ],
            "future_topics": [
                "خلافت راشدہ کے عدالتی اور مالیاتی نظام پر دستاویزی ویڈیو",
                "مسلم سائنسدانوں کے سائنسی کارنامے اور عالمی اثرات"
            ]
        }

ai_engine = AIEngine()
