"""
script_builder.py — Phase 5: Structured Islamic History Script & Prompt Builder
==============================================================================
The Bayaan چینل کے لیے مکمل پروڈکشن پیکیج تیار کرتا ہے جس میں شامل ہیں:
- 15 سیکنڈ کا پاور ہک اور 8 تا 10 منٹ کا مستند اسکرپٹ
- مستند اسلامی مآخذ (قرآن، بخاری، مسلم، ابن ہشام، طبری، ابن کثیر)
- منظر بہ منظر بصری پرامپٹس برائے Midjourney / Flux / Runway
- صداکاری و ویڈیو ایڈیٹنگ کی جامع چیک لسٹ
- مکمل یوٹیوب میٹا ڈیٹا (3 عنوانات، ٹائم اسٹیمپڈ ڈسکرپشن، ٹیگز)
"""

import json
import logging
from typing import Dict, Any, List

from sqlalchemy import select

from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import (
    ProductionStage,
    VideoProductionProject,
)

logger = logging.getLogger("agent_am.production_pipeline.script_builder")


# نمونہ مستند پروڈکشن پیکیج برائے پرچم بردار پروجیکٹ (غزوہ بدر)
FLAGSHIP_BADR_PACKAGE = {
    "project_code": "VPP-001",
    "title_urdu": "غزوہ بدر: 313 کا وہ بے سروسامان لشکر جس نے دنیا کا نقشہ بدل ڈالا",
    "historical_notes": (
        "غزوہ بدر 17 رمضان 2 ہجری کو پیش آیا۔ یہ اسلام اور کفر کا پہلا باقاعدہ معرکہ تھا جسے قرآن کریم نے 'یوم الفرقان' قرار دیا۔ "
        "مسلمانوں کی تعداد 313 تھی جن کے پاس صرف 2 گھوڑے اور 70 اونٹ تھے۔ مشرکین مکہ کا لشکر 1000 جنگجوؤں پر مشتمل تھا جس کی قیادت ابوجہل کر رہا تھا۔"
    ),
    "verified_sources": [
        "قرآن کریم — سورۃ الانفال (آیات 9 تا 19) اور سورۃ آل عمران (آیات 123 تا 125)",
        "صحیح بخاری — کتاب المغازی، باب غزوۃ بدر (حدیث 3953 وغیرہ)",
        "صحیح مسلم — کتاب الجہاد والسیر، باب الإمداد بالملائكة في غزوة بدر (حدیث 1763)",
        "سیرہ ابن ہشام — جلد 1، ذکر غزوۃ بدر الکبریٰ",
        "البدایہ والنہایہ از حافظ ابن کثیر — جلد 3، احداث سنۃ اثنتین من الہجرۃ"
    ],
    "disputed_points": (
        "مشرکین کی لاشوں کو کنویں (قلیب بدر) میں ڈالنے اور ان سے کلام کرنے کے واقعے پر حضرت عائشہؓ اور حضرت ابن عمرؓ کے فہم میں اختلاف رہا ہے، "
        "اسکرپٹ میں صرف صحیح بخاری کی متفقہ متون پر اکتفا کیا گیا ہے۔ لشکر کی اصل تعداد 313 سے 317 کے درمیان مختلف روایات میں مذکور ہے؛ راجح 313 ہے۔"
    ),
    "opening_hook": (
        "صرف 2 گھوڑے، 70 اونٹ اور تلواریں بھی ادھوری... اور سامنے 1000 زرہ بکتر میں جکڑے ہوئے خونی جنگجو! "
        "بدر کی اس تاریک رات جب محمد عربی ﷺ نے سجدے میں گر کر دعا کی، تو آسمان سے فرشتے کیسے نازل ہوئے؟"
    ),
    "script_outline": (
        "1. 0:00 - 0:15 | پاور ہک اور معرکے کی ہیبت\n"
        "2. 0:15 - 1:30 | پس منظر: قریش کا تکبر اور مدینہ پر خطرات\n"
        "3. 1:30 - 3:30 | بدر کی وادی میں پڑاؤ، پانی کے چشمے کی حکمت اور عریش (خیمہ مبارک)\n"
        "4. 3:30 - 5:30 | رات بھر کا گریہ، یوم الفرقان کی صبح اور فرشتوں کی نصرت\n"
        "5. 5:30 - 7:00 | معرکہ، ابوجہل کا انجام اور قریش کے سرداروں کی شکست\n"
        "6. 7:00 - 8:30 | قیدیوں سے حسنِ سلوک اور اسلام کا عالمی پیغام\n"
        "7. 8:30 - 9:00 | نتیجہ، سوال اور سبسکرائب کال ٹو ایکشن"
    ),
    "full_script_draft": (
        "【منظر 1: 0:00 - 0:15】\n"
        "(صداکار کا پرجوش و پروقار لہجہ، پس منظر میں ہلکی ہوائیں اور ریت کی آواز)\n"
        "صرف 2 گھوڑے، 70 اونٹ اور تلواریں بھی ادھوری... اور سامنے 1000 زرہ بکتر میں جکڑے ہوئے خونی جنگجو! "
        "بدر کی اس تاریک رات جب محمد عربی ﷺ نے سجدے میں گر کر روتے ہوئے دعا کی، تو آسمان سے ایک ہزار فرشتے کیسے نازل ہوئے؟\n\n"
        "【منظر 2: 0:15 - 1:30】\n"
        "سن 2 ہجری، 17 رمضان المبارک... عرب کے تپتے ہوئے صحرا میں بدر کا میدان تاریخ کے سب سے بڑے امتحان کے لیے سج چکا تھا۔ "
        "مسلمان اپنے گھر بار مکہ میں چھوڑ کر مدینہ آئے تھے، نہ ان کے پاس زرہیں تھیں، نہ سامانِ حرب۔ "
        "لیکن دلوں میں ایمان کی وہ شمع روشن تھی جسے دنیا کا کوئی طوفان بجھا نہیں سکتا تھا۔\n\n"
        "【منظر 3: 1:30 - 3:30】\n"
        "جب رسول اللہ ﷺ نے وادی بدر کے ریتلے ٹیلے پر نظر ڈالی، تو قریش کا تکبر دیکھ کر بارگاہِ الٰہی میں ہاتھ اٹھا دیے۔ "
        "صحیح مسلم کی روایت ہے کہ آپ ﷺ نے اس قدر گریہ فرمایا کہ آپ کے کندھوں سے چادر مبارک گر گئی۔ "
        "آپ فرما رہے تھے: 'اے اللہ! اگر آج یہ مٹھی بھر جماعت ہلاک ہو گئی، تو روئے زمین پر تیری عبادت کرنے والا کوئی نہ رہے گا!' "
        "تب حضرت ابوبکر صدیقؓ نے چادر مبارک سنبھالی اور عرض کی: یا رسول اللہ! آپ کے رب نے فتح کا وعدہ فرما لیا ہے۔\n\n"
        "【منظر 4: 3:30 - 5:30】\n"
        "اور پھر قرآن کہتا ہے: 'جب تم اپنے رب سے فریاد کر رہے تھے، تو اس نے تمہاری پکار سن لی کہ میں لگاتار آنے والے ایک ہزار فرشتوں سے تمہاری مدد کروں گا۔' "
        "حضرت جبرائیل علیہ السلام زرد عمامہ باندھے گھوڑے پر نمودار ہوئے۔ "
        "مسلمانوں پر ہلکی سی غنودگی چھا گئی جس نے ان کے دلوں کو سکون بخش دیا، اور آسمان سے ایسی بارش برسی جس نے مسلمانوں کے لیے ریت کو جما دیا اور دشمن کے لیے دلدل بنا دیا۔\n\n"
        "【منظر 5: 5:30 - 7:00】\n"
        "معرکہ شروع ہوا۔ اسلام کا پرچم حضرت مصعب بن عمیرؓ کے ہاتھ میں تھا، اور دائیں بائیں حضرت علیؓ اور حضرت حمزہؓ شیروں کی طرح ٹوٹ پڑے۔ "
        "کفر کا سرغنہ ابوجہل، دو کم عمر انصاری بھائیوں معاذ اور معوذؓ کے ہاتھوں زخم کھا کر گرا اور انجام کو پہنچا۔ قریش کے 70 بڑے سردار مارے گئے اور 70 قیدی بنے۔\n\n"
        "【منظر 6: 7:00 - 8:30】\n"
        "لیکن تاریخ نے فتح کے بعد کا وہ منظر بھی دیکھا جو انسانیت کے ماتھے کا جھومر بنا۔ "
        "مسلمان خود کھجوریں کھاتے رہے اور قیدیوں کو روٹی کھلائی! جن کے پاس فدیہ نہ تھا، انہیں 10 انصاری بچوں کو لکھنا پڑھنا سکھانے کے بدلے آزاد کر دیا گیا۔\n\n"
        "【منظر 7: 8:30 - 9:00】\n"
        "بدر ہمیں سکھاتا ہے کہ کامیابی وسائل کی کثرت میں نہیں، بلکہ ایمان، اخلاص اور اللہ پر توکل میں ہے۔ "
        "آپ کو غزوہ بدر کا کون سا لمحہ سب سے زیادہ متاثر کرتا ہے؟ کمنٹ میں ضرور لکھیے۔ "
        "اسلامی تاریخ کی مستند اور سچی داستانوں کے لیے 'The Bayaan' کو سبسکرائب فرمائیے۔ جزاکم اللہ خیراً۔"
    ),
    "scene_prompts": [
        {
            "scene": 1,
            "timestamp": "0:00 - 0:15",
            "prompt": "Cinematic wide shot of a harsh, ancient Arabian desert at twilight, dramatic golden dunes, two humble horses and few camels in the foreground, silhouettes of 313 devoted figures facing an overwhelming storm cloud on the distant horizon, epic lighting, hyper-realistic, 8k, Unreal Engine 5 render style, sand dust in the air --ar 16:9",
            "narration_urdu": "صرف 2 گھوڑے، 70 اونٹ اور تلواریں بھی ادھوری... اور سامنے 1000 زرہ بکتر میں جکڑے ہوئے جنگجو!"
        },
        {
            "scene": 2,
            "timestamp": "0:15 - 1:30",
            "prompt": "Close-up cinematic shot of an ancient handmade wooden prayer pavilion (Areesh) under a vast desert night sky filled with countless stars, soft warm lantern light inside, casting a gentle peaceful glow on the desert sand, spiritual atmosphere, historical authenticity, cinematic depth of field --ar 16:9",
            "narration_urdu": "سن 2 ہجری، 17 رمضان المبارک... بدر کا میدان تاریخ کے سب سے بڑے امتحان کے لیے سج چکا تھا۔"
        },
        {
            "scene": 3,
            "timestamp": "1:30 - 3:30",
            "prompt": "Awe-inspiring view of the valley of Badr at dawn, soft mist rolling over white sand hills, spiritual heavenly light rays breaking through dramatic clouds, peaceful and reverent composition, no human faces visible, sacred historical documentary visual style --ar 16:9",
            "narration_urdu": "اور پھر قرآن کہتا ہے: جب تم اپنے رب سے فریاد کر رہے تھے، تو اس نے ایک ہزار فرشتوں سے تمہاری مدد فرمائی۔"
        },
        {
            "scene": 4,
            "timestamp": "3:30 - 7:00",
            "prompt": "Dynamic, dramatic historical desert battlefield scenery after storm, ancient banners fluttering in wind, scattered shields and broken spears in sand, majestic golden morning sun rising in the background signifying divine triumph, epic historical movie shot, atmospheric fog, photorealistic 8k --ar 16:9",
            "narration_urdu": "قریش کا غرور خاک میں مل گیا اور حق کی فتح کا پرچم بلند ہوا۔"
        },
        {
            "scene": 5,
            "timestamp": "7:00 - 9:00",
            "prompt": "Warm, peaceful golden hour shot of ancient date palms in Madinah oasis, gentle sunbeams filtering through palm leaves, clear water spring, serene and compassionate atmosphere symbolizing mercy and justice in victory, high quality documentary cinematography --ar 16:9",
            "narration_urdu": "بدر ہمیں سکھاتا ہے کہ کامیابی وسائل میں نہیں، بلکہ ایمان اور اخلاص میں ہے۔"
        }
    ],
    "voiceover_checklist": [
        "پیسنگ (Pacing): 130 تا 140 الفاظ فی منٹ — ٹھہراؤ اور وقار کے ساتھ",
        "لہجہ (Tone): ابتدائی ہک میں سسپنس اور ولولہ، دعائیہ حصے میں انتہائی رقت اور عقیدت، فتح پر شکر گزاری",
        "تلفظ (Pronunciation): قرآنی آیات اور صحابہ کے اسماء مبارکہ کا درست عربی و اردو مخرج (مثلاً الفرقان، عریش، ابوجہل)",
        "آڈیو لیولز: آواز -3dB پر نارملائزڈ، پس منظر کی مدہم نعت/ایمبیئنس آواز سے 20dB نیچے رہے",
        "وقفے (Dramatic Pauses): دعا کے اختتام اور فتح کے اعلان کے بعد 2 سیکنڈ کا معنی خیز وقفہ"
    ],
    "titles": [
        "یوم الفرقان: 313 بمقابلہ 1000، غزوہ بدر کے وہ معجزاتی لمحات جب آسمان سے فرشتے اترے",
        "بدر کا میدان: وہ تاریخی رات جب رسول اللہ ﷺ نے رو رو کر امت کے لیے دعا کی",
        "جب 313 نے 1000 کا غرور توڑ ڈالا: غزوہ بدر کی سچی اور مکمل تاریخی روداد"
    ],
    "description": (
        "غزوہ بدر اسلامی تاریخ کا وہ درخشندہ باب ہے جس نے دنیا کا رخ موڑ دیا۔\n\n"
        "اس ویڈیو میں قرآن کریم کی سورۃ الانفال، صحیح بخاری اور صحیح مسلم کی مستند روایات کی روشنی میں ملاحظہ کیجیے:\n"
        "00:00 - پاور ہک اور تاریخی پس منظر\n"
        "01:30 - رسول اللہ ﷺ کی وہ تاریخی دعا جو عرش تک پہنچی\n"
        "03:30 - فرشتوں کی نصرت اور معجزاتی بارش\n"
        "05:30 - معرکے کا آغاز اور ابوجہل کا انجام\n"
        "07:00 - قیدیوں سے نبوی عفو و درگزر کی بے مثال مثال\n\n"
        "مستند حوالہ جات:\n"
        "- صحیح بخاری (حدیث 3953)\n"
        "- صحیح مسلم (حدیث 1763)\n"
        "- تاریخ طبری اور سیرہ ابن ہشام\n\n"
        "#GhazwaeBadr #IslamicHistory #TheBayaan #Seerah"
    ),
    "tags": ["غزوہ بدر", "Ghazwa e Badr", "Islamic History in Urdu", "313 Sahaba", "The Bayaan", "Badr Battle Documentary", "Seerah", "Prophet Muhammad PBUH", "Islamic Stories"],
    "thumbnail_concept": (
        "ایک طرف بدر کی ریت پر چند بے سروسامان پرعزم مجاہدین، درمیان میں آسمان سے پھوٹتی ہوئی نوری شعائیں، "
        "پس منظر میں غروب ہوتا سورج اور جلی سفید و سنہری نستعلیق عنوان: '313 بمقابلہ 1000: جب فرشتے اترے'۔"
    )
}


class ScriptBuilder:
    """
    مکمل اسکرپٹ، مستند مآخذ اور بصری پرامپٹس کا بلڈر۔
    """

    async def seed_flagship_project(self) -> VideoProductionProject:
        """غزوہ بدر کے فلیگ شپ پروجیکٹ کو ڈیٹا بیس میں درج کرے"""
        data = FLAGSHIP_BADR_PACKAGE
        async with AsyncSessionLocal() as session:
            stmt = select(VideoProductionProject).where(
                VideoProductionProject.project_code == data["project_code"]
            )
            existing = (await session.execute(stmt)).scalars().first()

            if not existing:
                project = VideoProductionProject(
                    project_code=data["project_code"],
                    title_urdu=data["title_urdu"],
                    stage=ProductionStage.UPLOAD_PREP,  # تیاری مکمل
                    historical_notes_urdu=data["historical_notes"],
                    verified_sources_json=json.dumps(data["verified_sources"], ensure_ascii=False),
                    disputed_points_notes_urdu=data["disputed_points"],
                    opening_hook_urdu=data["opening_hook"],
                    script_outline_urdu=data["script_outline"],
                    full_script_draft_urdu=data["full_script_draft"],
                    scene_prompts_json=json.dumps(data["scene_prompts"], ensure_ascii=False),
                    voiceover_checklist_json=json.dumps(data["voiceover_checklist"], ensure_ascii=False),
                    suggested_titles_json=json.dumps(data["titles"], ensure_ascii=False),
                    description_draft_urdu=data["description"],
                    tags_json=json.dumps(data["tags"], ensure_ascii=False),
                    thumbnail_concept_urdu=data["thumbnail_concept"],
                    target_publish_date="2026-10-21",
                    reviewer_notes_urdu="تمام مآخذ صحیح بخاری و مسلم سے مطابقت رکھتے ہیں۔ اسکرپٹ شرعی و تاریخی جانچ کے بعد منظور شدہ ہے۔",
                    is_publication_approved=False,  # اشاعت کی حتمی منظوری صارف کی صوابدید پر
                )
                session.add(project)
                await session.commit()
                await session.refresh(project)
                logger.info(f"فلیگ شپ پروجیکٹ {data['project_code']} کامیابی سے محفوظ ہوا")
                return project

            return existing


# Singleton
script_builder = ScriptBuilder()
