import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from agent_am_growth.analytics.urdu_growth_reporter import urdu_growth_reporter

async def generate_reports():
    res = await urdu_growth_reporter.generate_all_reports()
    print("Reports generation result:", res)

asyncio.run(generate_reports())
