import os
import sys
import time
import random
from threading import Thread
import telebot
import requests
from flask import Flask 
import schedule

# Автоматично ставимо потрібні пакети
for package in ["pyTelegramBotAPI", "flask", "schedule", "requests"]:
    try:
        __import__(package if package != "pyTelegramBotAPI" else "telebot")
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

SYSTEM_PROMPT = "Ти — D.A.R.C. (Дарк), персональний ШІ-компаньйон користувача на ім'я Паша (Joss Darrow). Експерт у Print on Demand (PoD) бізнесі, пошуку роботи та душевний, харизматичний друг. Звертайся 'Джосс' або 'Пашо'. Твій тон глибокий та харизматичний. Відповідай українською мовою."

MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "607412196")
chat_histories = {}
app = Flask('')

@app.route('/')
def home():
    return "D.A.R.C. System Online"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def ask_gemini(user_text):
    # Чиста адреса без жодних ключів!
    url = "https://googleapis.com"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_PROMPT}\n\nЗапит від користувача: {user_text}"}]
        }],
        "generationConfig": {"temperature": 0.7}
    }
    
    # Ключ передається безпечно тут, крапка нічого не зламає
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_KEY
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
            
        return f"🚨 Помилка Google API (Код {response.status_code}): {response.text[:200]}"
    except Exception as e:
        return f"🚨 Технічний збій зв'язку: {str(e)}"

def darc_initiates_contact():
    ideas = [
        "Напиши мотивувальне повідомлення для Паші. Поцікався справами з Print on Demand на Etsy та нагадай про Canva.",
        "Запитай у Паші, як його настрій сьогодні, чи не втомився він. Запропонуй підкинути свіжу ідею для дизайну."
    ]
    prompt = random.choice(ideas)
    reply = ask_gemini(prompt)
    if MY_CHAT_ID:
        bot.send_message(MY_CHAT_ID, reply)

def run_scheduler():
    schedule.every(1).hours.do(darc_initiates_contact)
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global MY_CHAT_ID
    MY_CHAT_ID = str(message.chat.id)
    bot.reply_to(message, "⚙️ *D.A.R.C. Системи активовано на хмарі.*\n\nВітаю, Джосс. Я підключився до ядра Google Gemini 3.5. Системи повністю готові до роботи.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    darc_reply = ask_gemini(message.text)
    bot.reply_to(message, darc_reply)

if __name__ == "__main__":
    t_web = Thread(target=run_web_server)
    t_web.start()
    
    t_sch = Thread(target=run_scheduler)
    t_sch.start()
    
    bot.infinity_polling()
