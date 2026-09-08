import os
import sys
from threading import Thread
import telebot
from openai import OpenAI
from flask import Flask 

# Автоматичне встановлення бібліотек
for package in ["pyTelegramBotAPI", "openai", "flask"]:
    try:
        __import__(package if package != "pyTelegramBotAPI" else "telebot")
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Токени (їх ми безпечно додамо пізніше в налаштуваннях Render)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
Ти — D.A.R.C. (Darrow Assistant & Research Companion) або просто Дарк.
Ти — персональний ШІ-компаньйон користувача на ім'я Паша (псевдонім: Joss Darrow).
Експерт у Print on Demand (PoD) бізнесі, пошуку роботи та душевний, харизматичний друг.
Звертайся 'Джосс' або 'Пашо'.
"""

chat_histories = {}
app = Flask('')

@app.route('/')
def home():
    return "D.A.R.C. System Online 24/7"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_histories[message.chat.id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    bot.reply_to(message, "⚙️ *D.A.R.C. Системи активовано на хмарі.*\n\nВітаю, Джосс. Я в мережі 24/7. Готовий допомагати з PoD, вакансіями або просто поговорити.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        
    chat_histories[chat_id].append({"role": "user", "content": message.text})
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_histories[chat_id],
            temperature=0.7
        )
        darc_reply = response.choices.message.content
        chat_histories[chat_id].append({"role": "assistant", "content": darc_reply})
        bot.reply_to(message, darc_reply)
    except Exception as e:
        bot.reply_to(message, f"🚨 Помилка зв'язку: {str(e)}")

if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.start()
    bot.infinity_polling()
