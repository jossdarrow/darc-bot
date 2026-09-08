import os
import sys
import time
import random
from threading import Thread
import telebot
from openai import OpenAI
from flask import Flask 
import schedule

# Автоматичне встановлення бібліотек
for package in ["pyTelegramBotAPI", "openai", "flask", "schedule"]:
    try:
        __import__(package if package != "pyTelegramBotAPI" else "telebot")
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

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

# Твій особистий ID чату (Дарк дізнається його автоматично при першому старті)
MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "607412196") # Сюди підставиться твій ID

chat_histories = {}
app = Flask('')

@app.route('/')
def home():
    return "D.A.R.C. System Online 24/7"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ФУНКЦІЯ АВТОНОМНОГО ЗВЕРНЕННЯ ДАРКА ---
def darc_initiates_contact():
    # Список тем, про які Дарк може написати сам
    ideas = [
        "Напиши коротке мотивувальне повідомлення для Паші. Поцікався, як просуваються справи з бізнесом Print on Demand, і нагадай, що Canva чекає на нові шедеври. Будь харизматичним.",
        "Запитай у Паші, як його настрій сьогодні, чи не втомився він. Запропонуй зробити перерву на каву або підкинути свіжу ідею для дизайну футболок.",
        "Напиши Паші з пропозицією згенерувати новий лістинг чи підібрати SEO-теги для Etsy/Amazon. Нагадай йому, що регулярність — ключ до продажів у PoD."
    ]
    
    prompt = random.choice(ideas)
    
    try:
        response = ai_client.chat.completions.create(
            model="gemini-3.5-flash-lite",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )
        darc_reply = response.choices.message.content
        
        # Надсилаємо Паші повідомлення першими!
        # Використовуємо збережений ID чату
        global chat_histories
        if MY_CHAT_ID:
            if MY_CHAT_ID not in chat_histories:
                chat_histories[MY_CHAT_ID] = [{"role": "system", "content": SYSTEM_PROMPT}]
            chat_histories[MY_CHAT_ID].append({"role": "assistant", "content": darc_reply})
            bot.send_message(MY_CHAT_ID, darc_reply)
    except Exception as e:
        print(f"Помилка ініціативи Дарка: {e}")

# Розклад: перевіряти кожну годину, і з шансом 25% писати в період з 12:00 до 19:00
def plan_checking():
    current_hour = time.localtime().tm_hour
    if 12 <= current_hour <= 19:
        if random.random() < 0.25: # 25% шанс, що напише саме в цю годину
            darc_initiates_contact()

def run_scheduler():
    # Перевірка раз на годину
    schedule.every(1).hours.do(plan_checking)
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- СТАНДАРТНА ЛОГІКА ЧАТУ ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global MY_CHAT_ID
    MY_CHAT_ID = str(message.chat.id)
    chat_histories[message.chat.id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    bot.reply_to(message, "⚙️ *D.A.R.C. Системи активовано на хмарі.*\n\nВітаю, Джосс. Протокол автономних сповіщень активовано. Тепер я на зв'язку та стежитиму за трендами.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        
    chat_histories[chat_id].append({"role": "user", "content": message.text})
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        response = ai_client.chat.completions.create(
           model="gemini-3.5-flash-lite",
            messages=chat_histories[chat_id],
            temperature=0.7
        )
        darc_reply = response.choices.message.content
        chat_histories[chat_id].append({"role": "assistant", "content": darc_reply})
        bot.reply_to(message, darc_reply)
    except Exception as e:
        bot.reply_to(message, f"🚨 Помилка: {str(e)}")

if __name__ == "__main__":
    t_web = Thread(target=run_web_server)
    t_web.start()
    
    # Запуск таймера в окремому потоці
    t_sch = Thread(target=run_scheduler)
    t_sch.start()
    
    bot.infinity_polling()
