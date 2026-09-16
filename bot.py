import os
import re
import feedparser
import requests
from deep_translator import GoogleTranslator

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@kibritmedia")

print(f"Target Channel: {CHANNEL_USERNAME}")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN is missing!")

RSS_URLS = [
    "https://tg.i-c-a.su/rss/topor",
    "https://tg.i-c-a.su/rss/shedevrplus"
]
STATE_FILE = "sent_ids.txt"

def clean_message(text):
    # Remove all types of links, domains, and telegram mentions
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"www\.\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"t\.me/\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[a-zA-Z0-9.-]+\.(com|ru|org|net|az|io|me|cc|info|biz)\b\S*", "", text, flags=re.IGNORECASE)
    
    # Remove unwanted symbols and channel signatures
    text = re.sub(r"[👉👇📢🔥💥⚡️]", "", text)
    text = re.sub(r"@(?:topor|топор|shedevrplus|şedevrplus|\w+)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:topor|топор|shedevrplus|şedevrplus).*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"Подписаться.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\.{2,}", ".", text)
    
    # Clean spaces per line while preserving paragraph breaks (newlines)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def translate_text(text):
    if not text:
        return text
    try:
        print("Translating paragraph by paragraph via Google Translate...")
        paragraphs = text.split("\n")
        translated_paragraphs = []
        for p in paragraphs:
            if p.strip():
                translated = GoogleTranslator(source='auto', target='az').translate(p)
                translated_paragraphs.append(translated if translated else p)
            else:
                translated_paragraphs.append("")
        return "\n".join(translated_paragraphs)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def get_sent_ids():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_id(post_id):
    sent = list(get_sent_ids())
    if post_id not in sent:
        sent.append(post_id)
        if len(sent) > 100:
            sent = sent[-100:]
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(sent))

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
    sent_ids = get_sent_ids()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for rss_url in RSS_URLS:
        print(f"Checking RSS feed: {rss_url}")
        try:
            response = requests.get(rss_url, headers=headers, timeout=15)
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                if feed.entries:
                    entry = feed.entries[0]
                    post_id = entry.get("id") or entry.get("link") or entry.get("title")
                    
                    if post_id in sent_ids:
                        print(f"Post {post_id} already sent. Skipping.")
                    else:
                        raw_text = entry.get("summary", "") or entry.get("title", "")
                        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
                        raw_text = re.sub(r"</p>", "\n\n", raw_text, flags=re.IGNORECASE)
                        raw_text = re.sub(r"<.*?>", "", raw_text)
                        
                        cleaned = clean_message(raw_text)

                        if cleaned:
                            translated_text = translate_text(cleaned)
                            final_text = f"❗ {translated_text}"
                            
                            res = send_to_channel(final_text)
                            if res and res.get("ok"):
                                print(f"SUCCESS: Posted new message from {rss_url}!")
                                save_sent_id(post_id)
                                sent_ids.add(post_id)
                            else:
                                print(f"FAILED to post to Telegram: {res}")
                        else:
                            print("Cleaned text is empty, skipping.")
                else:
                    print("Feed entries list is empty.")
            else:
                print(f"Failed to fetch RSS, status code: {response.status_code}")
        except Exception as e:
            print(f"Error processing RSS {rss_url}: {e}")
            
    print("Script execution completed.")
