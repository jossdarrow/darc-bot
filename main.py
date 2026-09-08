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

SYSTEM_PROMPT = """
Ти — D.A.R.C. (Darrow Assistant & Research Companion) або просто Дарк.
Ти — персональний ШІ-компаньйон користувача на ім'я Паша (псевдонім: Joss Darrow).
Експерт у Print on Demand (PoD) бізнесі, пошуку роботи та душевний, харизматичний друг.
Звертайся 'Джосс' або 'Пашо'. Відповідай українською мовою. Твій тон глибокий та харизматичний.
"""

MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "607412196")
chat_histories = {}
app = Flask('')

@app.route('/')
def home():
    return "D.A.R.C. System Online 24/7"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def ask_gemini(messages_list):
    url = f"https://googleapis.com{GEMINI_KEY}"
    contents = []
    for msg in messages_list:
        role_map = "user" if msg["role"] == "user" else "model"
        if msg["role"] == "system":
            continue
        contents.append({
            "role": role_map,
            "parts": [{"text": msg["content"]}]
        })
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {"temperature": 0.7}
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        res_json = response.json()
        try:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "🚨 Дарк: Отримано некоректну структуру відповіді від ядра."
    else:
        return f"🚨 Помилка ядра Gemini (Код {response.status_code}): {response.text}"

def darc_initiates_contact():
    ideas = [
        "Напиши коротке мотивувальне повідомлення для Паші. Поцікався, як просуваються справи з бізнесом Print on Demand, і нагадай, що Canva чекає на нові шедеври.",
        "Запитай у Паші, як його настрій сьогодні, чи не втомився він. Запропонуй зробити перерву на каву або підкинути свіжу ідею для дизайну футболок."
    ]
    prompt = random.choice(ideas)
    reply = ask_gemini([{"role": "user", "content": prompt}])
    global chat_histories
    if MY_CHAT_ID:
        if MY_CHAT_ID not in chat_histories:
            chat_histories[MY_CHAT_ID] = []
        chat_histories[MY_CHAT_ID].append({"role": "assistant", "content": reply})
        bot.send_message(MY_CHAT_ID, reply)

def plan_checking():
    current_hour = time.localtime().tm_hour
    if 12 <= current_hour <= 19:
        if random.random() < 0.25:
            darc_initiates_contact()

def run_scheduler():
    schedule.every(1).hours.do(plan_checking)
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global MY_CHAT_ID
    MY_CHAT_ID = str(message.chat.id)
    chat_histories[message.chat.id] = []
    bot.reply_to(message, "⚙️ *D.A.R.C. Системи активовано на хмарі.*\n\nВітаю, Джосс. Я підключився напряму до ядра Google Gemini. Протокол зв'язку стабільний.", parse_mode="Markdown")

@bot.message_handler(commands=['reset'])
def reset_chat(message):
    chat_histories[message.chat.id] = []
    bot.reply_to(message, "🧠 Пам'ять Дарка очищена.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
    chat_histories[chat_id].append({"role": "user", "content": message.text})
    bot.send_chat_action(chat_id, 'typing')
    darc_reply = ask_gemini(chat_histories[chat_id])
    chat_histories[chat_id].append({"role": "assistant", "content": darc_reply})
    bot.reply_to(message, darc_reply)

if __name__ == "__main__":
    t_web = Thread(target=run_web_server)
    t_web.start()
    t_sch = Thread(target=run_scheduler)
    t_sch.start()
    bot.infinity_polling()

