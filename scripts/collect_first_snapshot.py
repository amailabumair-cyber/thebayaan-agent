import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from agent_am_growth.analytics.metrics_collector import metrics_collector

async def collect_first_snapshot():
    print("Channel snapshot collecting...")
    ch = await metrics_collector.collect_live_channel_snapshot()
    print(f"Channel: success={ch.success}, errors={ch.errors}")
    if ch.channel_snapshot:
        s = ch.channel_snapshot
        print(f"  subscribers={s.subscribers}, views={s.total_views}, videos={s.video_count}")

    print("Video snapshots collecting...")
    vid = await metrics_collector.collect_live_video_snapshots()
    print(f"Videos: success={vid.success}, saved={vid.videos_saved}, errors={vid.errors}")

asyncio.run(collect_first_snapshot())
