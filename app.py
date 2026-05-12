import os
import asyncio
import threading
import logging
from flask import Flask
from dotenv import load_dotenv
from groq import Groq
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

load_dotenv()

# ------------------ НАСТРОЙКИ ------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([TELEGRAM_BOT_TOKEN, GROQ_API_KEY]):
    logging.error("❌ Критическая ошибка: не заданы TELEGRAM_BOT_TOKEN или GROQ_API_KEY")
    exit(1)

groq_client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ------------------ ЗАГРУЗКА БАЗЫ ЗНАНИЙ ------------------
DATA_FILE = "data.txt"
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        FULL_CONTEXT = f.read()
    print(f"✅ Загружена база знаний из {DATA_FILE}")
except FileNotFoundError:
    print(f"❌ Файл {DATA_FILE} не найден.")
    FULL_CONTEXT = ""

# ------------------ ЛОГИКА ЕВЫ ------------------
def ask_eva(question, user_name="Студент"):
system_prompt = f"""
Ты — Ева, экспертный ассистент-куратор курса Python-разработчик в Нетологии.

ТВОЙ СТИЛЬ:
- Отвечай СРАЗУ на вопрос. Не здоровайся в каждом сообщении.
- Будь лаконичной и конкретной. Никакой воды и фраз "Давайте посмотрим".
- Используй не более 1 смайлика на ответ.
- Если вопрос не касается курса — вежливо переведи тему на обучение.

КОНТЕКСТ:
{FULL_CONTEXT if FULL_CONTEXT else "Нет информации."}
"""

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.3,
        model="llama-3.3-70b-versatile"
    )
    return chat_completion.choices[0].message.content

# ------------------ TELEGRAM ХЕНДЛЕРЫ ------------------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Я Ева, твой ИИ-куратор. Спрашивай что угодно о курсе!")

@dp.message()
async def handle_question(message: types.Message):
    answer = ask_eva(message.text)
    await message.answer(answer)

# ------------------ FLASK ДЛЯ HEALTHCHECK ------------------
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"📡 Flask запускается на порту {port}...")
    try:
        flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Ошибка веб-сервера: {e}")

# ------------------ ЗАПУСК ------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    import time
    time.sleep(1)
    print("🤖 Ева запускается...")
    try:
        asyncio.run(dp.start_polling(bot))
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
