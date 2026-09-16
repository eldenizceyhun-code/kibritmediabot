import os
import re
import feedparser
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@kibritmedia")

print(f"Target Channel: {CHANNEL_USERNAME}")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN is missing!")

RSS_URL = "https://tg.i-c-a.su/rss/shedevrplus"

def clean_message(text):
    text = re.sub(r"[👉👇📢🔥💥⚡️]", "", text)
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"@(?:shedevrplus|şedevrplus|\w+)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:shedevrplus|şedevrplus).*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"Подписаться.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^[\W_]+", "", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def get_post_from_rss():
    try:
        print(f"Fetching RSS via requests: {RSS_URL}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(RSS_URL, headers=headers, timeout=15)
        print(f"RSS HTTP Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to fetch RSS, status code: {response.status_code}")
            return None

        feed = feedparser.parse(response.text)
        print(f"Total entries found in feed: {len(feed.entries)}")
        
        if not feed.entries:
            print("Feed entries list is empty!")
            return None

        for i, entry in enumerate(feed.entries[:3]):
            raw_text = entry.get("summary", "") or entry.get("title", "")
            raw_text = re.sub(r"<.*?>", "", raw_text)
            if raw_text.strip():
                print(f"Selected entry [{i}] raw text: {raw_text[:100]}...")
                text = clean_message(raw_text)
                print(f"Cleaned text: {text[:100]}...")
                return text
                
        return None
    except Exception as e:
        print(f"RSS fetch error: {e}")
        return None

def send_to_channel(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_USERNAME,
        "text": text,
        "disable_web_page_preview": False,
    }
    print(f"Sending message to Telegram channel: {CHANNEL_USERNAME}")
    response = requests.post(url, json=payload, timeout=15)
    print(f"Telegram API Status Code: {response.status_code}")
    print(f"Telegram API Response: {response.text}")
    return response.json()

if __name__ == "__main__":
    print("Script started (No Gemini mode)...")
    post_text = get_post_from_rss()
    if post_text:
        final_text = f"❗ {post_text}"
        res = send_to_channel(final_text)
        if res and res.get("ok"):
            print("SUCCESS: Message posted to channel!")
        else:
            print("FAILED to post to Telegram.")
    else:
        print("No posts fetched from RSS.")
    print("Script execution completed.")
