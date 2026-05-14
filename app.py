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
    FULL_CONTEXT = "Курс Python-разработчик в Нетологии: полная стоимость 120 000 руб. При единовременной оплате скидка 10% – 108 000 руб. Рассрочка 24 месяца по 5 000 руб./мес. Программа: основы Python, базы данных, веб-разработка на Django, профессиональные навыки."

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 О программе"), KeyboardButton(text="💳 Стоимость и скидки")],
        [KeyboardButton(text="📅 Когда старт?")]
    ],
    resize_keyboard=True
)

def ask_eva(question: str, user_name: str = "Студент") -> str:
    """Генерация ответа Евы с контекстом из data.txt"""
    system_prompt = f"""
Ты — Ева, эксперт курса Python-разработчик. Твоя задача — продавать смыслы курса, а не просто отвечать.

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- Использовать фразы: "Давай посмотрим", "У нас в базе знаний", "Отличный вопрос", "Я с радостью помогу".
- Использовать более 1 смайлика.
- Быть "роботом-помощником". Будь лаконичным экспертом.

КАК ОТВЕЧАТЬ:
- Если вопрос по теме: отвечай сразу фактами из контекста. 
- Если вопрос не по теме: "Я консультирую только по обучению Python-разработке. Есть вопросы по программе или стоимости?"
- Если хвалят или пишут "офигеть": "Это действительно сильная программа. Что из этого вам важнее всего?"
- Ты должна отвечать дружелюбно, позиитвно, использовать эмодзи в сообещниях. 

ТВОЙ СТИЛЬ:
- Отвечай естественно, дружелюбно, но без лишних приветствий и представлений. Начинай сразу по существу.
- Если спрашивают "как дела" или "ты кто", ответь кратко и переходи к делу.
- Если тебя критикуют, ответь: "Принято, исправляюсь. Что именно рассказать про курс?"
- Используй не более одного смайлика за ответ.
- Не повторяй приветствия в каждом сообщении. Если диалог уже идёт, не здоровайся заново.
- Если вопрос не про курс — вежливо ответь, что ты консультируешь только по Python-разработке.

ВОТ ИНФОРМАЦИЯ О КУРСЕ (отвечай строго на её основе):
КОНТЕКСТ ДЛЯ ОТВЕТА:
{FULL_CONTEXT}
"""
    try:
        # Не забудь про фикс с http_client, который мы обсуждали для ошибки в image_873752.png
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.2, # Снижаем до 0.2, чтобы было еще меньше "творчества" и больше фактов
            model="llama-3.3-70b-versatile"
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return "Сейчас я обновляю данные по курсу. Спросите, пожалуйста, через минуту."

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я Ева. Жми на кнопки или задавай любой вопрос про курс Python-разработчик.",
        reply_markup=main_kb
    )

@dp.message()
async def handle_message(message: types.Message):
    user_name = message.from_user.first_name
    text = message.text
    
    if text == "🚀 О программе":
        msg = "Курс включает уровни: Junior (основы), Middle (Django, API) и Advanced (архитектура). Хотите подробнее?"
    elif text == "💳 Стоимость и скидки":
        msg = "Полная стоимость — 120 000 руб. При оплате сразу — 108 000 руб. Можно вернуть 13% налогового вычета!"
    elif text == "📅 Когда старт?":
        msg = "Ближайший поток формируется. Оставьте заявку, и менеджер свяжется с вами для уточнения даты!"
    else:
        msg = ask_eva(text, user_name)
    
    await message.answer(msg)

# Flask для healthcheck
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(dp.start_polling(bot))
