import os
import time
import threading
import telebot
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR KEEP-ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    # Zeabur provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- BOT LOGIC ---
# Get token from Environment Variable for security
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Fish Bot is active on Zeabur! 24/7 Mode Enabled.")

# Import your game logic here or paste the optimized code below
# (For now, I'll keep it simple, you can replace this part with the full optimized game logic)

def start_bot():
    print("Bot is starting...")
    while True:
        try:
            bot.polling(none_stop=True, interval=3, timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    keep_alive()  # Start the web server
    start_bot()   # Start the bot
