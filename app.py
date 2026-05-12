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
# Загружаем data.txt один раз при старте (кешируем)
DATA_FILE = "data.txt"
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        FULL_CONTEXT = f.read()
    print(f"✅ Загружена база знаний из {DATA_FILE} ({len(FULL_CONTEXT)} символов)")
except FileNotFoundError:
    print(f"❌ Файл {DATA_FILE} не найден. Бот будет работать без контекста.")
    FULL_CONTEXT = ""

# ------------------ ЛОГИКА С ОДНИМ КОНТЕКСТОМ ------------------
def ask_eva(question, user_name="Студент"):
    system_prompt = f"""
Ты — Ева, профессиональный ассистент-куратор курса Python-разработчик в Нетологии.
Ты общаешься со студентом по имени {user_name}.

ТВОЙ СТИЛЬ:
- Деловой, лаконичный, грамотный.
- Минимум воды. Сначала суть, потом детали.
- Используй не более ОДНОГО смайлика на всё сообщение (и то, если он уместен).
- Не будь слишком слащавой. Ты — эксперт, а не аниматор.

ПРАВИЛА ОТВЕТОВ:
1. Отвечай ТОЛЬКО на основе предоставленного КОНТЕКСТА.
2. Если в контексте нет информации — честно скажи: "В моей базе знаний этого нет, уточню у команды".
3. Форматируй списки и важные цифры (цены, даты), чтобы их было легко читать.

КОНТЕКСТ:
{FULL_CONTEXT}
"""

КОНТЕКСТ:
{FULL_CONTEXT if FULL_CONTEXT else "Контекст пуст. Ответьте, что нет информации."}
"""

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.3,  # чуть выше 0 для лёгкой гибкости, но без галлюцинаций
        model="llama-3.3-70b-versatile"
    )
    return chat_completion.choices[0].message.content

# ------------------ TELEGRAM ХЕНДЛЕРЫ ------------------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я Ева, AI-куратор Нетологии. \nЗадай мне вопрос о курсе Python-разработчик.\n\n"
        "Примеры вопросов:\n• Сколько стоит курс?\n• Какая программа обучения?\n• Когда старт?"
    )

@dp.message()
async def handle_question(message: types.Message):
    user_name = message.from_user.first_name
    answer = ask_eva(message.text, user_name)
    await message.answer(answer)

# ------------------ FLASK ДЛЯ HEALTHCHECK ------------------
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    # Render передает нужный порт в переменную окружения PORT. 
    # Если её нет, берем 10000 (стандарт для Render).
    port = int(os.environ.get("PORT", 10000))
    print(f"📡 Flask запускается на порту {port}...")
    try:
        # Важно: host="0.0.0.0" позволяет внешнему миру видеть Flask
        flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Ошибка веб-сервера: {e}")
        
# ------------------ ЗАПУСК ------------------
if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    # Даём Flask небольшую фору
    import time
    time.sleep(1)
    # Запускаем бота
    print("🤖 Ева запускается...")
    try:
        asyncio.run(dp.start_polling(bot))
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
