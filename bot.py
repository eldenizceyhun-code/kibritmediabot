import os
import re
import feedparser
import google.generativeai as genai
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@kibritmedia")

print(f"Target Channel: {CHANNEL_USERNAME}")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN is missing!")

# Gemini API configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found! Please check GitHub Secrets.")

genai.configure(api_key=GEMINI_API_KEY)

system_instruction = (
    "You are a professional Azerbaijani news editor and translator. "
    "Translate and adapt the provided text ABSOLUTELY AND ONLY into fluent, natural, grammatically flawless Azerbaijani literary language. "
    "NEVER reply in Russian or Turkish! Use only pure Azerbaijani literary language. "
    "Completely clean out all links, channel names, citations, and promotional sentences from the text. "
    "Keep only the core essence of the news and write a concise, meaningful, and readable summary of maximum 5-6 sentences without over-expanding. "
    "Do not write any extra introductions, headings, quotes, or output remarks; return only the cleanly translated and summarized news text."
)

generation_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction
)

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

def translate_and_polish_with_gemini(text):
    try:
        print("Sending request to Gemini API...")
        prompt = f"Translate the following news into pure Azerbaijani language and write a short, concise summary with a maximum of 5-6 sentences:\n\n{text}"
        response = generation_model.generate_content(prompt)
        result = response.text.strip()
        print("Gemini response received successfully.")
        return result
    except Exception as e:
        print("GEMINI ERROR:", type(e).__name__, str(e))
        return None

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

        # Ən son 3 xəbəri yoxlayaq və ilk mətni olanı götirək
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
    print("Script started for shedevrplus...")
    post_text = get_post_from_rss()
    if post_text:
        polished_text = translate_and_polish_with_gemini(post_text)
        if polished_text:
            final_text = f"❗ {polished_text}"
            res = send_to_channel(final_text)
            if res and res.get("ok"):
                print("SUCCESS: Message posted to channel!")
            else:
                print("FAILED to post to Telegram.")
        else:
            print("Gemini translation returned empty.")
    else:
        print("No posts fetched from RSS.")
    print("Script execution completed.")
