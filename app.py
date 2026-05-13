import os
import asyncio
import threading
import logging
from flask import Flask
from dotenv import load_dotenv
from groq import Groq
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ------------------ НАСТРОЙКИ ------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([TELEGRAM_BOT_TOKEN, GROQ_API_KEY]):
    logger.error("❌ Критическая ошибка: не заданы ключи")
    exit(1)

groq_client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ------------------ ДАННЫЕ ------------------
DATA_FILE = "data.txt"
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        FULL_CONTEXT = f.read()
    logger.info(f"✅ Загружен файл {DATA_FILE}, длина {len(FULL_CONTEXT)} символов")
except FileNotFoundError:
    logger.warning(f"⚠️ Файл {DATA_FILE} не найден, использую дефолтный контекст")
    FULL_CONTEXT = "Информация о курсе Python-разработчик в Нетологии: стоимость 120к, скидка 10%, рассрочка на 24 мес."

# ------------------ ЛОГИКА ЕВЫ ------------------
def ask_eva(question: str, user_name: str = "Студент") -> str:
    # Улучшенный системный промпт (без запрещённых фраз в тексте, позитивные инструкции)
    system_prompt = f"""
Ты — Ева, эксперт и ассистент курса Python-разработчик в Нетологии. Ты общаешься с будущим студентом по имени {user_name}.

ТВОЙ СТИЛЬ:
- Отвечай естественно, дружелюбно, но без лишних приветствий и представлений. Начинай сразу по существу.
- Если спрашивают "как дела" или "ты кто", ответь кратко и переходи к делу.
- Если тебя критикуют, ответь: "Принято, исправляюсь. Что именно рассказать про курс?"
- Используй не более одного смайлика за ответ.
- Не повторяй приветствия в каждом сообщении. Если диалог уже идёт, не здоровайся заново.

ОТВЕТЫ ОСНОВЫВАЙ НА ЭТОЙ ИНФОРМАЦИИ:
{FULL_CONTEXT}
"""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.6,
            model="llama-3.3-70b-versatile"
        )
        answer = chat_completion.choices[0].message.content
        # Небольшая очистка: убираем возможные повторяющиеся приветствия, которые модель иногда выдаёт
        if answer.startswith(("Привет!", "Здравствуйте!", "Добрый день!", "Рада помочь")):
            # убираем первую фразу до точки или запятой, но проще заменить на пустоту
            parts = answer.split(",", 1)
            if len(parts) > 1:
                answer = parts[1].lstrip()
        return answer.strip()
    except Exception as e:
        logger.error(f"Ошибка при вызове Groq: {e}")
        return "Извините, сейчас технические трудности. Попробуйте позже."

# ------------------ TELEGRAM ХЕНДЛЕРЫ ------------------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_name = message.from_user.first_name or "Студент"
    await message.answer(f"Привет, {user_name}! Я Ева — твой помощник по курсу Python-разработчик в Нетологии. Что хочешь узнать?")

@dp.message()
async def handle_question(message: types.Message):
    user_name = message.from_user.first_name or "Студент"
    answer = ask_eva(message.text, user_name)
    await message.answer(answer)

# ------------------ FLASK ДЛЯ HEALTHCHECK ------------------
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
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("🚀 Ева запущена и готова к общению!")
    # Запускаем поллинг бота
    asyncio.run(dp.start_polling(bot))
