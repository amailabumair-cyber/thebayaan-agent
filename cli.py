"""
Agent AM - Urdu CLI (کمانڈ لائن انٹرفیس)
ٹرمینل کے ذریعے براہِ راست اردو ہدایات دینے کا ذریعہ
"""

import sys
import asyncio

# ونڈوز کنسول میں اردو کی درست نمائش کے لیے UTF-8 سیٹ کریں
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_am.database.connection import init_db
from agent_am.core.commands import urdu_commands
from agent_am.config.settings import settings

async def main():
    await init_db()
    args = sys.argv[1:]

    if not args:
        print(f"=== خوش آمدید! {settings.AGENT_NAME} برائے '{settings.CHANNEL_NAME}' ===")
        print("اردو میں اپنی کمانڈ ٹائپ کریں (مثال: 'روزانہ آڈٹ شروع کریں' یا 'exit' برائے خروج):")
        while True:
            try:
                cmd = input("\n[Agent AM] > ").strip()
                if not cmd or cmd.lower() in ["exit", "quit", "بند کریں"]:
                    break
                res = await urdu_commands.handle_command(cmd)
                print("\n" + res.get("message_urdu", str(res)))
            except (KeyboardInterrupt, EOFError):
                break
        print("\nاللہ حافظ!")
        return

    first_arg = args[0].lower()
    command_map = {
        "audit": "روزانہ آڈٹ شروع کریں",
        "report": "آج کی رپورٹ دکھائیں",
        "queue": "اگلے دو دن کی پوسٹس دکھائیں",
        "status": "ایجنٹ کا سسٹم اسٹیٹس دکھائیں",
        "quiz": "نئی کوئز پوسٹ تیار کریں",
        "poll": "نیا ٹیکسٹ پول تیار کریں",
        "failed": "ناکام کاموں کی تفصیل دکھائیں",
        "verify": "شیڈول شدہ پوسٹس کی تصدیق کریں"
    }

    cmd_urdu = command_map.get(first_arg, " ".join(args))
    res = await urdu_commands.handle_command(cmd_urdu)
    print("\n" + res.get("message_urdu", str(res)))

if __name__ == "__main__":
    asyncio.run(main())
