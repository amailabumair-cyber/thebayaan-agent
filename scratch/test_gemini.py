import sys
sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import asyncio
from agent_am.services.ai_engine import ai_engine

async def main():
    try:
        res = await ai_engine._query_llm(
            "You are an Islamic scholar.",
            'Generate a JSON response: {"text": "السلام علیکم"}'
        )
        print("Gemini response:", res)
    except Exception as e:
        print("Gemini error:", e)

if __name__ == "__main__":
    asyncio.run(main())
