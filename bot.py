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
STATE_FILE = "last_id.txt"

def clean_message(text):
    # Remove all types of links, domains, and telegram mentions
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"www\.\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"t\.me/\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[a-zA-Z0-9.-]+\.(com|ru|org|net|az|io|me|cc|info|biz)\b\S*", "", text, flags=re.IGNORECASE)
    
    # Remove unwanted emojis, checkmarks, symbols, and channel signatures
    text = re.sub(r"[👉👇📢🔥💥⚡️✅✔️📌❗]", "", text)
    text = re.sub(r"@(?:shedevrplus|şedevrplus|\w+)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:shedevrplus|şedevrplus).*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"Подписаться.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\.{2,}", ".", text)
    
    # Clean spaces per line while preserving paragraph breaks (newlines)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def get_last_sent_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_last_sent_id(post_id):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(post_id))

def send_to_channel(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_USERNAME,
        "text": text,
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=15)
    return response.json()

if __name__ == "__main__":
    print("Checking Shedevrplus RSS feed (without translation)...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(RSS_URL, headers=headers, timeout=15)
    
    if response.status_code == 200:
        feed = feedparser.parse(response.text)
        if feed.entries:
            entry = feed.entries[0]
            post_id = entry.get("id") or entry.get("link") or entry.get("title")
            last_sent = get_last_sent_id()

            print(f"Latest post ID: {post_id}")
            print(f"Last sent ID: {last_sent}")

            if post_id == last_sent:
                print("No new posts. Skipping.")
            else:
                raw_text = entry.get("summary", "") or entry.get("title", "")
                raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
                raw_text = re.sub(r"</p>", "\n\n", raw_text, flags=re.IGNORECASE)
                raw_text = re.sub(r"<.*?>", "", raw_text)
                
                cleaned = clean_message(raw_text)

                if cleaned:
                    res = send_to_channel(cleaned)
                    if res and res.get("ok"):
                        print("SUCCESS: Posted to channel!")
                        save_last_sent_id(post_id)
                    else:
                        print(f"FAILED to post to Telegram: {res}")
                else:
                    print("Cleaned text is empty, skipping.")
        else:
            print("Feed is empty.")
    else:
        print(f"Failed to fetch RSS, status code: {response.status_code}")
    print("Script execution completed.")
