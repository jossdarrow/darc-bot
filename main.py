import os
import sys
import time
import random
import base64
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

# Словник для збереження пам'яті діалогів (до 20 останніх повідомлень)
chat_histories = {}
app = Flask('')

@app.route('/')
def home():
    return "D.A.R.C. System Online"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def ask_gemini(chat_id, user_text, image_base64=None):
    # Офіційний endpoint для Gemini 3.5 Flash-Lite (підтримує пам'ять і картинки)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_KEY}"

    # Ініціалізуємо пам'ять для нового чату
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
        
    history = chat_histories[chat_id]

    # Формуємо поточне повідомлення від користувача
    user_parts = []
    if user_text:
        user_parts.append({"text": user_text})
    else:
        user_parts.append({"text": "Опиши цю картинку та дай поради щодо дизайну."})

    # Додаємо картинку, якщо вона є
    if image_base64:
        user_parts.append({
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": image_base64
            }
        })

    current_message = {"role": "user", "parts": user_parts}
    
    # Створюємо масив повідомлень: історія + поточний запит
    contents = history + [current_message]

    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {"temperature": 0.7}
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            res_json = response.json()
            bot_reply = res_json["candidates"][0]["content"]["parts"][0]["text"]
            
            # Зберігаємо запит та відповідь у пам'ять
            history.append(current_message)
            history.append({"role": "model", "parts": [{"text": bot_reply}]})
            
            # Очищаємо стару пам'ять, щоб не перевантажувати запит (залишаємо останні 20 реплік)
            if len(history) > 20:
                chat_histories[chat_id] = history[-20:]
                
            return bot_reply
            
        return f"🚨 Помилка Google API (Код {response.status_code}): {response.text[:200]}"
    except Exception as e:
        return f"🚨 Технічний збій зв'язку: {str(e)}"

def darc_initiates_contact():
    global MY_CHAT_ID
    if not MY_CHAT_ID:
        return
        
    history = chat_histories.get(MY_CHAT_ID, [])
    
    # Якщо в пам'яті вже є діалог, просимо Дарка продовжити тему
    if len(history) > 0:
        prompt = "[Внутрішній системний тригер]: Напиши мені першим. Проаналізуй наш останній діалог і спитай, як успіхи з тим, про що ми говорили. Або запропонуй свіжу ідею. Зроби це коротко, невимушено, як друг. Не кажи, що це тригер."
    else:
        # Якщо історія порожня
        prompt = "[Внутрішній системний тригер]: Напиши мені першим. Привітайся, запитай як мій настрій сьогодні і чи є натхнення щось створити. Будь харизматичним."
        
    # Відправляємо тригер у нашу ж функцію. 
    # Це згенерує відповідь і заразом збереже її в історію діалогу.
    reply = ask_gemini(MY_CHAT_ID, prompt)
    bot.send_message(MY_CHAT_ID, reply)

def run_scheduler():
    # Безкінечний цикл для фонового потоку
    while True:
        # Бот "спить" 30 хвилин (1800 секунд)
        time.sleep(1800)
        
        # Кидаємо віртуальний кубик (від 0.0 до 1.0)
        # Якщо випадає менше 0.10 (це і є 10% шанс) — Дарк ініціює контакт
        if random.random() < 0.10:
            try:
                darc_initiates_contact()
            except Exception as e:
                print(f"Помилка при ініціації контакту: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global MY_CHAT_ID
    MY_CHAT_ID = str(message.chat.id)
    # Очищуємо пам'ять при рестарті
    chat_histories[MY_CHAT_ID] = [] 
    bot.reply_to(message, "⚙️ *D.A.R.C. Системи активовано на хмарі.*\n\nВітаю, Джосс. Я підключився до ядра Google Gemini 3.5 Flash-Lite. Пам'ять та зорові модулі повністю готові до роботи.", parse_mode="Markdown")

# ОБРОБКА ТЕКСТУ
@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    darc_reply = ask_gemini(str(message.chat.id), message.text)
    bot.reply_to(message, darc_reply)

# ОБРОБКА ФОТОГРАФІЙ
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'upload_photo')
    try:
        # Отримуємо фото найвищої якості (останнє в масиві)
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Конвертуємо у base64 для Google API
        image_base64 = base64.b64encode(downloaded_file).decode('utf-8')
        
        # Беремо підпис до фотографії або ставимо дефолтний запит
        user_text = message.caption if message.caption else "Що скажеш про цю графіку?"
        
        darc_reply = ask_gemini(str(message.chat.id), user_text, image_base64)
        bot.reply_to(message, darc_reply)
    except Exception as e:
        bot.reply_to(message, f"🚨 Помилка обробки зображення: {str(e)}")

if __name__ == "__main__":
    t_web = Thread(target=run_web_server)
    t_web.start()
    
    t_sch = Thread(target=run_scheduler)
    t_sch.start()
    
    bot.infinity_polling()
