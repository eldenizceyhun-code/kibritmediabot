import os
import re
import feedparser
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@kibritmedia")

print(f"Target Channel: {CHANNEL_USERNAME}")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN is missing!")

# İzləniləcək kanalların siyahısı (Şedevr və Papirus)
SOURCES = [
    {
        "id": "shedevrplus",
        "rss": "https://tg.i-c-a.su/rss/shedevrplus",
        "state_file": "last_id_shedevrplus.txt"
    },
    {
        "id": "papirus",
        "rss": "https://tg.i-c-a.su/rss/P_apirus",
        "state_file": "last_id_papirus.txt"
    }
]

def clean_message(text):
    # Remove all types of links, domains, and telegram mentions
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"www\.\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"t\.me/\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[a-zA-Z0-9.-]+\.(com|ru|org|net|az|io|me|cc|info|biz)\b\S*", "", text, flags=re.IGNORECASE)
    
    # Remove unwanted emojis, checkmarks, symbols, and channel signatures
    text = re.sub(r"[👉👇📢🔥💥⚡️✅✔️📌❗]", "", text)
    text = re.sub(r"@(?:shedevrplus|şedevrplus|P_apirus|papirus|\w+)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:shedevrplus|şedevrplus|P_apirus|papirus).*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"Подписаться.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\.{2,}", ".", text)
    
    # Clean spaces per line while preserving paragraph breaks (newlines)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def get_last_sent_id(state_file):
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_last_sent_id(state_file, post_id):
    with open(state_file, "w", encoding="utf-8") as f:
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for source in SOURCES:
        source_id = source["id"]
        rss_url = source["rss"]
        state_file = source["state_file"]
        
        print(f"\nChecking {source_id} RSS feed...")
        try:
            response = requests.get(rss_url, headers=headers, timeout=25)
            
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                if feed.entries:
                    entry = feed.entries[0]
                    post_id = entry.get("id") or entry.get("link") or entry.get("title")
                    last_sent = get_last_sent_id(state_file)

                    print(f"Latest post ID for {source_id}: {post_id}")
                    print(f"Last sent ID for {source_id}: {last_sent}")

                    if post_id == last_sent:
                        print(f"No new posts for {source_id}. Skipping.")
                    else:
                        raw_text = entry.get("summary", "") or entry.get("title", "")
                        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
                        raw_text = re.sub(r"</p>", "\n\n", raw_text, flags=re.IGNORECASE)
                        raw_text = re.sub(r"<.*?>", "", raw_text)
                        
                        cleaned = clean_message(raw_text)

                        if cleaned:
                            res = send_to_channel(cleaned)
                            if res and res.get("ok"):
                                print(f"SUCCESS: Posted new item from {source_id} to channel!")
                                save_last_sent_id(state_file, post_id)
                            else:
                                print(f"FAILED to post {source_id} to Telegram: {res}")
                        else:
                            print(f"Cleaned text for {source_id} is empty, skipping.")
                else:
                    print(f"Feed for {source_id} is empty.")
            else:
                print(f"Failed to fetch RSS for {source_id}, status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Network or Timeout error for {source_id}: {e}")
            continue
            
    print("\nScript execution completed.")

