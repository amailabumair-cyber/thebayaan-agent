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
        catalog = [
            {
                "topic": "غزوہ احد",
                "keywords": ["احد", "uhud", "جبل احد"],
                "question": "غزوہ احد میں رسول اللہ ﷺ نے تیر اندازوں کے دستے کو کس اہم پہاڑی پر تعینات فرمایا تھا؟",
                "options": ["جبلِ رماۃ (عینین)", "کوہِ احد", "جبلِ ثور", "جبلِ نور"],
                "correct_answer": "جبلِ رماۃ (عینین)",
                "explanation": "رسول اللہ ﷺ نے حضرت عبداللہ بن جبیرؓ کی قیادت میں 50 تیر اندازوں کو جبل رماۃ پر مقرر فرمایا تھا اور حکم دیا تھا کہ ہر حال میں جگہ نہ چھوڑیں۔",
                "source_reference": "صحیح البخاری، کتاب المغازی / سیرت ابن ہشام"
            },
            {
                "topic": "غزوہ خندق",
                "keywords": ["خندق", "احزاب", "khandaq"],
                "question": "غزوہ خندق (معرکہ احزاب) میں مدینہ منورہ کے دفاع کے لیے خندق کھودنے کا تاریخی مشورہ کس جلیل القدر صحابی نے دیا تھا؟",
                "options": ["حضرت سلمان فارسی رضی اللہ عنہ", "حضرت علی بن ابی طالب رضی اللہ عنہ", "حضرت عمر فاروق رضی اللہ عنہ", "حضرت ابو عبیدہ بن الجراح رضی اللہ عنہ"],
                "correct_answer": "حضرت سلمان فارسی رضی اللہ عنہ",
                "explanation": "حضرت سلمان فارسیؓ نے اہل فارس کے جنگی طریقے کے مطابق خندق کھودنے کی تجویز پیش کی جسے رسول اللہ ﷺ نے پسند فرمایا۔",
                "source_reference": "تاریخ طبری، جلد دوم / البدایہ والنہایہ، جلد چہارم"
            },
            {
                "topic": "حضرت عمر فاروق",
                "keywords": ["عمر", "فاروق", "umar"],
                "question": "امیر المؤمنین حضرت عمر بن الخطاب رضی اللہ عنہ کے دورِ خلافت میں اسلامی سنِ ہجری تقویم کا آغاز کس تاریخی واقعے کی بنیاد پر کیا گیا؟",
                "options": ["ہجرتِ مدینہ منورہ", "فتحِ مکہ مکرمہ", "ولادتِ باسعادت", "بیعتِ عقبہ ثانیہ"],
                "correct_answer": "ہجرتِ مدینہ منورہ",
                "explanation": "سن 16 ہجری میں حضرت عمر فاروقؓ نے صحابہ کرامؓ کے مشورے سے سن ہجری کا آغاز رسول اللہ ﷺ کی ہجرت مدینہ کے سال سے مقرر فرمایا۔",
                "source_reference": "تاریخ الخلفاء از علامہ جلال الدین سیوطی / البدایہ والنہایہ"
            },
            {
                "topic": "حضرت عثمان غنی",
                "keywords": ["عثمان", "غنی", "ذوالنورین", "usman"],
                "question": "امیر المؤمنین حضرت عثمان غنی رضی اللہ عنہ کے عظیم ترین کارناموں میں قرآن کریم کی کس خدمت کو تاریخ میں امتیازی مقام حاصل ہے؟",
                "options": ["مصحف عثمانی کی نقل و ترسیل", "پہلی تفسیر قرآن لکھوانا", "قرآن کریم کا پہلا مدرسہ", "قرآن کے اعراب لگوانا"],
                "correct_answer": "مصحف عثمانی کی نقل و ترسیل",
                "explanation": "حضرت عثمان غنیؓ نے امت کو ایک قراءت اور مصحفِ واحد پر جمع فرما کر مختلف اسلامی صوبوں میں سرکاری نسخے روانہ فرمائے۔",
                "source_reference": "صحیح البخاری، کتاب فضائل القرآن"
            },
            {
                "topic": "حضرت علی مرتضیٰ و خیبر",
                "keywords": ["علی", "خیبر", "مرتضی", "ali", "khaibar"],
                "question": "غزوہ خیبر میں رسول اللہ ﷺ نے یہود کے سب سے مضبوط قلعہ (قموص) کی فتح کے لیے اسلامی پرچم کس جلیل القدر صحابی کے دست مبارک میں عطا فرمایا؟",
                "options": ["حضرت علی بن ابی طالب رضی اللہ عنہ", "حضرت زبیر بن عوام رضی اللہ عنہ", "حضرت خالد بن ولید رضی اللہ عنہ", "حضرت سعد بن ابی وقاص رضی اللہ عنہ"],
                "correct_answer": "حضرت علی بن ابی طالب رضی اللہ عنہ",
                "explanation": "رسول اللہ ﷺ نے فرمایا: کل میں ایسے شخص کو جھنڈا دوں گا جس کے ہاتھ پر اللہ فتح عطا کرے گا، جو اللہ اور اس کے رسول سے محبت رکھتا ہے اور اللہ اور اس کا رسول اس سے محبت رکھتے ہیں۔",
                "source_reference": "صحیح مسلم، کتاب فضائل الصحابہ / صحیح البخاری"
            },
            {
                "topic": "سلطان صلاح الدین ایوبی",
                "keywords": ["صلاح الدین", "ایوبی", "حطین", "قدس", "salahuddin"],
                "question": "سلطان صلاح الدین ایوبی رحمہ اللہ نے صلیبیوں کو کس فیصلہ کن معرکے میں شکست دے کر 88 سال بعد بیت المقدس کو آزاد کرایا تھا؟",
                "options": ["معرکہ حطین (583ھ)", "معرکہ ملازکرد (463ھ)", "معرکہ عین جالوت (658ھ)", "معرکہ زلاقہ (479ھ)"],
                "correct_answer": "معرکہ حطین (583ھ)",
                "explanation": "معرکہ حطین 4 جولائی 1187ء (583ھ) کو پیش آیا جس کے بعد سلطان نے 27 رجب کو بیت المقدس پر اسلامی پرچم لہرایا۔",
                "source_reference": "النوادر السلطانیۃ از قاضی ابن شداد / الکامل فی التاریخ"
            },
            {
                "topic": "غزوہ بدر",
                "keywords": ["بدر", "badr"],
                "question": "غزوہ بدر اسلامی تاریخ کا پہلا فیصلہ کن معرکہ تھا۔ یہ کس ہجری سال میں پیش آیا؟",
                "options": ["2 ہجری", "3 ہجری", "5 ہجری", "8 ہجری"],
                "correct_answer": "2 ہجری",
                "explanation": "غزوہ بدر 17 رمضان المبارک 2 ہجری بمطابق 624 عیسوی کو پیش آیا جس میں مسلمانوں کو فتح نصیب ہوئی۔",
                "source_reference": "تاریخ طبری، جلد دوم / البدایہ والنہایہ، جلد سوم"
            },
            {
                "topic": "حضرت ابوبکر صدیق",
                "keywords": ["ابوبکر", "صدیق", "abubakr"],
                "question": "رسول اللہ ﷺ کے وصال کے بعد فتنہ ارتداد اور منکرین زکوٰۃ کے خلاف فیصلہ کن جنگ کا تاریخی عزم کس خلیفہ راشد نے فرمایا؟",
                "options": ["حضرت ابو بکر صدیق رضی اللہ عنہ", "حضرت عمر فاروق رضی اللہ عنہ", "حضرت عثمان غنی رضی اللہ عنہ", "حضرت علی مرتضیٰ رضی اللہ عنہ"],
                "correct_answer": "حضرت ابو بکر صدیق رضی اللہ عنہ",
                "explanation": "حضرت ابوبکر صدیقؓ نے تاریخی الفاظ کہے: 'اگر وہ ایک رسی بھی روکیں گے جو رسول اللہ ﷺ کو دیتے تھے تو میں ان کے خلاف جہاد کروں گا۔'",
                "source_reference": "صحیح البخاری، کتاب الزکوٰۃ / البدایہ والنہایہ"
            },
            {
                "topic": "تاریخ اندلس و طارق بن زیاد",
                "keywords": ["اندلس", "طارق", "سپین", "tariq"],
                "question": "فاتح اندلس طارق بن زیاد نے 711 عیسوی (92ھ) میں سپین کے ساحل پر اتر کر کس مشہور مقام پر اپنی فوج کا پہلا مرکز قائم کیا؟",
                "options": ["جبل الطارق (Gibraltar)", "قرطبہ (Cordoba)", "طلیطلہ (Toledo)", "غرناطہ (Granada)"],
                "correct_answer": "جبل الطارق (Gibraltar)",
                "explanation": "طارق بن زیاد نے جس چٹان اور پہاڑ پر پڑاؤ ڈالا وہ ان کے نام سے منسوب ہو کر آج تک 'جبل الطارق' (Gibraltar) کہلاتا ہے۔",
                "source_reference": "تاریخ اندلس از ابن عذاری / نفح الطیب از مقری"
            },
            {
                "topic": "فتح مکہ",
                "keywords": ["فتح مکہ", "مکہ", "makkah"],
                "question": "فتح مکہ کے پرامن اور تاریخی دن مسلمانوں کا 10 ہزار پر مشتمل لشکر کس ہجری سال میں مکہ مکرمہ داخل ہوا تھا؟",
                "options": ["8 ہجری", "6 ہجری", "9 ہجری", "10 ہجری"],
                "correct_answer": "8 ہجری",
                "explanation": "20 رمضان المبارک 8 ہجری کو مکہ مکرمہ بغیر کسی بڑے خون خرابے کے فتح ہوا اور رسول اللہ ﷺ نے عام معافی کا اعلان فرمایا۔",
                "source_reference": "سیرت ابن ہشام / زاد المعاد از ابن القیم"
            },
            {
                "topic": "حضرت خالد بن ولید",
                "keywords": ["خالد", "یرموک", "سیف اللہ", "khalid"],
                "question": "معرکہ یرموک میں رومی سلطنت کے 2 لاکھ کے لشکر کے مقابلے میں 40 ہزار مسلمانوں کی عسکری صف بندی کس سپہ سالار نے ترتیب دی تھی؟",
                "options": ["حضرت خالد بن ولید رضی اللہ عنہ", "حضرت ابو عبیدہ بن الجراح رضی اللہ عنہ", "حضرت عمرو بن العاص رضی اللہ عنہ", "حضرت شرحبیل بن حسنہ رضی اللہ عنہ"],
                "correct_answer": "حضرت خالد بن ولید رضی اللہ عنہ",
                "explanation": "حضرت خالد بن ولیدؓ نے فوج کو کردوس (بریگیڈز) میں تقسیم کر کے ایسی تاریخی جنگی حکمت عملی اپنائی جس نے رومی سلطنت کی کمر توڑ دی۔",
                "source_reference": "فتوح الشام از واقدی / تاریخ طبری"
            }
        ]

        # اگر خاص مطلوبہ موضوع دیا گیا ہو تو کی ورڈ کے ذریعے تلاش کریں
        if target_topic:
            norm_target = target_topic.strip().lower()
            for item in catalog:
                for kw in item.get("keywords", []):
                    if kw in norm_target or norm_target in kw:
                        item["content_hash"] = self.compute_content_hash(item["question"], item["options"])
                        return item

        # ورنہ حالیہ موضوعات کو مدنظر رکھ کر انتخاب کریں
        for item in catalog:
            if not recent_topics or item["topic"] not in recent_topics:
                item["content_hash"] = self.compute_content_hash(item["question"], item["options"])
                return item

        item = catalog[0]
        item["content_hash"] = self.compute_content_hash(item["question"], item["options"])
        return item

    def _get_verified_fallback_poll(self, recent_topics: List[str] = None, target_topic: Optional[str] = None) -> Dict[str, Any]:
        catalog = [
            {
                "topic": "شخصیات",
                "keywords": ["شخصیات", "صحابہ", "فاتحین", "خالد", "علی", "عمر"],
                "question": "مسلم تاریخ کے عظیم فاتحین اور شخصیات میں سے آپ اگلی تفصیلی دستاویزی ویڈیو کس پر دیکھنا پسند فرمائیں گے؟",
                "options": [
                    "حضرت خالد بن ولید رضی اللہ عنہ (سیف اللہ)",
                    "سلطان صلاح الدین ایوبی رحمہ اللہ (فاتح بیت المقدس)",
                    "حضرت علی المرتضیٰ رضی اللہ عنہ (شجاعت و علم)",
                    "سلطان محمد فاتح رحمہ اللہ (فاتح قسطنطنیہ)"
                ],
                "explanation": "ناظرین کی ترجیحات اور آئندہ شخصیات کا انتخاب",
                "source_reference": "دی بیان تاریخی سلسلہ"
            },
            {
                "topic": "معرکے",
                "keywords": ["معرکے", "جنگ", "بدر", "احد", "یرموک", "قادسیہ", "خندق"],
                "question": "اسلامی تاریخ کے عظیم دفاعی معرکوں میں سے کس معرکے کی حکمت عملی اور سٹریٹیجی آپ کو سب سے زیادہ متاثر کرتی ہے؟",
                "options": [
                    "غزوہ بدر (ایمان بمقابلہ مادی طاقت)",
                    "معرکہ یرموک (رومی سلطنت کے خلاف فیصلہ کن فتح)",
                    "معرکہ قادسیہ (ساسانی ایران کی شکست)",
                    "غزوہ خندق (دفاعی حکمت عملی کا شاہکار)"
                ],
                "explanation": "تاریخی معرکوں پر ناظرین کی رائے اور دلچسپی",
                "source_reference": "دی بیان عسکری تاریخ"
            },
            {
                "topic": "ادوار",
                "keywords": ["ادوار", "اندلس", "عثمانی", "خلافت", "عباسی"],
                "question": "'The Bayan' پر آپ اسلامی تاریخ کے کس سنہری دور پر اگلی تفصیلی ویڈیو دیکھنا پسند کریں گے؟",
                "options": [
                    "خلافت راشدہ کی فتوحات اور عدل و انصاف کا نظام",
                    "اندلس (مسلم سپین) کا سنہری علمی و سائنسی دور",
                    "سلطنت عثمانیہ کا 600 سالہ عروج اور فتوحات",
                    "عہد عباسی اور بغداد کے علمی مراکز (بیت الحکمہ)"
                ],
                "explanation": "ناظرین کی ترجیحات اور تاریخی ادوار کا جائزہ",
                "source_reference": "دی بیان چینل سروے"
            }
        ]

        if target_topic:
            norm_target = target_topic.strip().lower()
            for item in catalog:
                for kw in item.get("keywords", []):
                    if kw in norm_target or norm_target in kw:
                        item["content_hash"] = self.compute_content_hash(item["question"], item["options"])
                        return item

            # اگر صارف کا موضوع مخصوص ہو تو اس کے لیے خودکار کسٹم پول بنائیں
            custom_poll = {
                "question": f"اسلامی تاریخ میں '{target_topic}' کے اہم پہلوؤں میں سے آپ کو کس پر تفصیلی دستاویزی ویڈیو درکار ہے؟",
                "options": [
                    f"{target_topic} کا تاریخی پس منظر اور ابتدا",
                    f"{target_topic} کے اہم واقعات اور حقائق",
                    f"{target_topic} سے حاصل ہونے والے اسباق و عبرت",
                    f"موجودہ دور کے لیے {target_topic} کا پیغام"
                ],
                "explanation": f"موضوع '{target_topic}' پر ناظرین کی ترجیحات",
                "source_reference": "دی بیان ناظرین سروے",
                "topic": target_topic
            }
            custom_poll["content_hash"] = self.compute_content_hash(custom_poll["question"], custom_poll["options"])
            return custom_poll

        for item in catalog:
            if not recent_topics or item["topic"] not in recent_topics:
                item["content_hash"] = self.compute_content_hash(item["question"], item["options"])
                return item

        item = catalog[0]
        item["content_hash"] = self.compute_content_hash(item["question"], item["options"])
        return item

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
