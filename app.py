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
    logging.error("❌ Критическая ошибка: не заданы ключи")
    exit(1)

groq_client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ------------------ ДАННЫЕ ------------------
DATA_FILE = "data.txt"
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        FULL_CONTEXT = f.read()
except FileNotFoundError:
    FULL_CONTEXT = "Информация о курсе Python-разработчик в Нетологии: стоимость 120к, скидка 10%, рассрочка на 24 мес."

# ------------------ ЛОГИКА ЕВЫ ------------------
def ask_eva(question):
    # Промпт максимально очищен от мусора
    system_prompt = f"""
Ты — Ева, эксперт и ассистент курса Python-разработчик в Нетологии. Ты общаешься с будущим студентом.

ТВОИ ПРАВИЛА (СТРОГО):
1. ЗАПРЕЩЕНО использовать фразы: "база знаний", "в моих данных", "я посмотрю", "уточню у менеджера".
2. Отвечай так, будто ты сама всё это знаешь наизусть. 
3. На простые вопросы ("как дела", "ты кто") отвечай как человек — кратко и дружелюбно.
4. Если тебя критикуют ("не тупи", "плохо"), отвечай: "Принято, исправляюсь. Что именно рассказать про курс?".
5. Используй максимум 1 смайлик. Будь лаконичной.

ИНФОРМАЦИЯ ДЛЯ ТЕБЯ:
{FULL_CONTEXT}
"""

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.6,  # Еще чуть выше, чтобы была "живее"
        model="llama-3.3-70b-versatile"
    )
    return chat_completion.choices[0].message.content

# ------------------ TELEGRAM ------------------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Я Ева. Готова рассказать всё о курсе Python-разработчик. Что тебя интересует?")

@dp.message()
async def handle_question(message: types.Message):
    answer = ask_eva(message.text)
    await message.answer(answer)

# ------------------ FLASK (HEALTH) ------------------
flask_app = Flask(__name__)
@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ------------------ ЗАПУСК ------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🤖 Ева в эфире...")
    asyncio.run(dp.start_polling(bot))
