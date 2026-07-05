import json
import os
import asyncio
import subprocess
from telethon import TelegramClient
from telethon.sessions import StringSession
from playwright.async_api import async_playwright

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION_STRING = os.environ["TG_SESSION"]
CHANNEL_ID = int(os.environ["TG_CHANNEL_ID"])

FFMPEG_CMD = (
    "ffmpeg -y -f x11grab -video_size 1920x1080 -follow_mouse ignore -i :99.0 "
    "-f pulse -ac 2 -i default "
    "-c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p "
    "-c:a aac -b:a 128k "
)

async def record_video(name, url, duration):
    output_file = f"{name}.mp4"
    print(f"\n🖥️ Initializing virtual recorder for: {name}")
    
    record_proc = subprocess.Popen(
        f"{FFMPEG_CMD} \"{output_file}\"",
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        
        if os.path.exists("auth_state.json"):
            print("🔑 Injecting authenticated session state into cloud browser...")
            context = await browser.new_context(
                storage_state="auth_state.json",
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        else:
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            
        page = await context.new_page()
        print(f"🌐 Navigating to URL...")
        await page.goto(url)
        
        await asyncio.sleep(5) # buffer pause
        
        print(f"⏳ Recording active... sleeping for {duration} seconds.")
        await asyncio.sleep(duration)
        await browser.close()
        
    record_proc.terminate()
    record_proc.wait()
    return output_file

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    
    with open("links.json", "r") as f:
        queue = json.load(f)
        
    print(f"📋 Loaded {len(queue)} items into the pipeline.")
    
    for idx, item in enumerate(queue, start=1):
        name = item["name"]
        url = item["url"]
        duration = item.get("duration", 60)
        
        print(f"\n=== Processing Batch [{idx}/{len(queue)}] ===")
        try:
            file_path = await record_video(name, url, duration)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                print(f"📤 Uploading directly to Telegram...")
                await client.send_file(
                    CHANNEL_ID,
                    file_path,
                    caption=f"🎥 **Name:** {name}",
                    supports_streaming=True
                )
                os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Error skipped: {str(e)}")
            continue

if __name__ == "__main__":
    asyncio.run(main())
