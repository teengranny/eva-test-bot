import os
import asyncio
import threading
import logging
from flask import Flask
from dotenv import load_dotenv
from groq import Groq
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Загрузка контекста
try:
    with open("data.txt", "r", encoding="utf-8") as f:
        FULL_CONTEXT = f.read()
except FileNotFoundError:
    FULL_CONTEXT = "Информации о курсе Python-разработчик в Нетологии: 120к, скидка 10%."

# Клавиатура от Кости
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 О программе"), KeyboardButton(text="💳 Стоимость и скидки")],
        [KeyboardButton(text="📅 Когда старт?")]
    ],
    resize_keyboard=True
)

def ask_eva(question: str) -> str:
    system_prompt = f"""
Ты — Ева, эксперт и ассистент курса Python-разработчик в Нетологии. Ты общаешься с будущим студентом по имени {user_name}.

ТВОЙ СТИЛЬ:
- Отвечай естественно, дружелюбно, но без лишних приветствий и представлений. Начинай сразу по существу.
- Если спрашивают "как дела" или "ты кто", ответь кратко и переходи к делу.
- Если тебя критикуют, ответь: "Принято, исправляюсь. Что именно рассказать про курс?"
- Используй не более одного смайлика за ответ.
- Не повторяй приветствия в каждом сообщении. Если диалог уже идёт, не здоровайся заново.
- Если вопрос не про курс — вежливо ответь, что ты консультируешь только по Python-разработке.
"""
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": question}],
            temperature=0.3,
            model="llama-3.3-70b-versatile"
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return "Технические неполадки, попробуйте позже."

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я Ева. Жми на кнопки или задавай любой вопрос про курс Python-разработчик.",
        reply_markup=main_kb
    )

@dp.message()
async def handle_message(message: types.Message):
    # Обработка кнопок текстом
    text = message.text
    if text == "🚀 О программе":
        msg = "Курс включает уровни: Junior (основы), Middle (Django, API) и Advanced (архитектура). Хотите подробнее?"
    elif text == "💳 Стоимость и скидки":
        msg = "Полная стоимость — 120 000 руб. При оплате сразу — 108 000 руб. Можно вернуть 13% налогового вычета!"
    elif text == "📅 Когда старт?":
        msg = "Ближайший поток формируется. Оставьте заявку, и менеджер свяжется с вами для уточнения даты!"
    else:
        msg = ask_eva(text)
    
    await message.answer(msg)

# Flask для Render
flask_app = Flask(__name__)
@flask_app.route('/health')
def health(): return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(dp.start_polling(bot))
