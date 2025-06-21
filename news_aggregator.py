from telethon import TelegramClient, events
import csv
from datetime import datetime, timedelta
import os
import google.generativeai as genai
import asyncio
import schedule
import time
import threading
import requests

# Configuration - Easy to change
SUMMARY_FREQUENCY_MINUTES = int(60 * 3)  # Change this to adjust how often summaries are generated

# Telegram API credentials
api_hash = os.environ['api_hash']
api_id = os.environ['api_id']
bot_token = os.environ['bot_token']
chat_id = os.environ['chat_id']  # Chat ID where summaries will be sent

# Gemini API setup
genai.configure(api_key=os.environ['gemini_api'])
model = genai.GenerativeModel('gemini-2.0-flash')

channels = ['t.me/amitsegal', 't.me/abualiexpress', 't.me/newsflashhhj']

client = TelegramClient('session_name', api_id, api_hash)


def send_telegram_message(message):
    """Send message to Telegram chat using bot"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("Summary sent successfully!")
        else:
            print(f"Failed to send message: {response.text}")
    except Exception as e:
        print(f"Error sending message: {e}")


def read_csv_messages(date_str):
    """Read messages from CSV file for a specific date"""
    filename = f'telegram_log_{date_str}.csv'
    messages = []

    if not os.path.exists(filename):
        return messages

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    timestamp, channel, message = row[0], row[1], row[2]
                    messages.append({
                        'timestamp': timestamp,
                        'channel': channel,
                        'message': message
                    })
    except Exception as e:
        print(f"Error reading CSV: {e}")

    return messages


def create_summary():
    """Create summary using Gemini API"""
    current_date = datetime.utcnow().date().isoformat()
    messages = read_csv_messages(current_date)

    if not messages:
        print("No messages found for today")
        return

    # Get messages from the last summary period
    time_ago = datetime.utcnow() - timedelta(minutes=SUMMARY_FREQUENCY_MINUTES)
    recent_messages = []

    for msg in messages:
        try:
            msg_time = datetime.fromisoformat(msg['timestamp'].replace(
                'Z', '+00:00'))
            if msg_time >= time_ago:
                recent_messages.append(msg)
        except:
            continue

    if not recent_messages:
        print("No recent messages found")
        return

    # Prepare messages for Gemini
    news_text = ""
    for msg in recent_messages:
        news_text += f"Channel: {msg['channel']}\nTime: {msg['timestamp']}\nMessage: {msg['message']}\n\n"

    # Create prompt for Gemini
    prompt = f"""
    אנא צור סיכום חדשות קצר מההודעות הבאות מטלגרם שנאספו ב-{SUMMARY_FREQUENCY_MINUTES} הדקות האחרונות.
    התמקד בפריטי החדשות החשובים ביותר וארגן אותם לפי נושא אם אפשר.
    
    הודעות:
    {news_text}
    
    אנא ספק סיכום מובנה בפורמט הבא:
    📰 **סיכום חדשות - {datetime.utcnow().strftime('%H:%M UTC')}**
    
    **כותרות עיקריות:**
    • [סיכום קצר של פריטי החדשות העיקריים]
    
    **עדכונים נוספים:**
    • [פריטים נוספים ראויים לציון]
    
    שמור על תמציתיות אך אינפורמטיביות. כתב בעברית.
    """

    try:
        response = model.generate_content(prompt)
        summary = response.text

        print("Summary generated:")
        print(summary)

        # Send summary to Telegram
        send_telegram_message(summary)

    except Exception as e:
        print(f"Error generating summary: {e}")


@client.on(events.NewMessage(chats=channels))
async def handler(event):
    message = event.message.message
    sender = await event.get_chat()
    channel_name = sender.username
    timestamp = datetime.utcnow().isoformat()

    current_date = datetime.utcnow().date().isoformat()

    # Create CSV file with headers if it doesn't exist
    filename = f'telegram_log_{current_date}.csv'
    file_exists = os.path.exists(filename)

    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'channel', 'message'])
        writer.writerow([timestamp, channel_name, message])


def run_scheduler():
    """Run the scheduler in a separate thread"""
    while True:
        schedule.run_pending()
        time.sleep(60)


async def main():
    # Schedule summary creation based on configured frequency
    schedule.every(SUMMARY_FREQUENCY_MINUTES).minutes.do(create_summary)

    # Start scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    print(
        f"News aggregator started. Collecting messages and creating summaries every {SUMMARY_FREQUENCY_MINUTES} minutes..."
    )

    # Start Telegram client
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
