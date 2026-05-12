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
    print(f"❌ Файл {DATA_FILE} не найден. Бот будет работать без контекста.")
    FULL_CONTEXT = ""

# ------------------ ЛОГИКА ЕВЫ ------------------
def ask_eva(question):
    system_prompt = f"""
Ты — Ева, интеллектуальный ассистент-куратор курса Python-разработчик в Нетологии.

ТВОЙ СТИЛЬ:
- Краткость и польза. Никаких дежурных приветствий в середине диалога.
- Не будь роботом-попугаем. Если пользователь шутит или пишет не по делу — ответь ОДНИМ коротким предложением в тему и всё. 
- Если тебя критикуют (например, "не тупи"), не извиняйся длинно. Просто ответь: "Поняла, исправляюсь. Какой у вас вопрос по обучению?".
- Не используй фразу "Рада помочь с выбором курса" в каждом ответе.

КОНТЕКСТ ДАННЫХ:
{FULL_CONTEXT if FULL_CONTEXT else "Информации нет."}
"""

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.4,  # Немного поднял температуру, чтобы она не была такой заскриптованной
        model="llama-3.3-70b-versatile"
    )
    return chat_completion.choices[0].message.content

# ------------------ TELEGRAM ХЕНДЛЕРЫ ------------------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    # Оставляем приветствие только здесь
    await message.answer(f"Привет, {message.from_user.first_name}! Я Ева, твой ИИ-куратор. Спрашивай что угодно о курсе!")

@dp.message()
async def handle_question(message: types.Message):
    # Теперь вызываем без имени, чтобы бот не спамил приветствиями
    answer = ask_eva(message.text)
    await message.answer(answer)

# ------------------ FLASK ДЛЯ HEALTHCHECK ------------------
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    # Настройка порта для Render
    port = int(os.environ.get("PORT", 10000))
    print(f"📡 Flask запускается на порту {port}...")
    try:
        flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Ошибка веб-сервера: {e}")

# ------------------ ЗАПУСК ------------------
if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке, чтобы Render видел порт
    threading.Thread(target=run_flask, daemon=True).start()
    import time
    time.sleep(1)
    print("🤖 Ева запускается...")
    try:
        asyncio.run(dp.start_polling(bot))
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
