import os
import asyncio
import threading
import logging
import httpx
from flask import Flask
from dotenv import load_dotenv
from groq import Groq
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Инициализация Groq с фиксом прокси
http_client = httpx.Client()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"), http_client=http_client)
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

# ПАМЯТЬ БОТА
user_history = {}

# АКТУАЛЬНЫЙ КОНТЕКСТ (Данные Нетологии на май 2026)
FULL_CONTEXT = """
1. КУРС PYTHON-РАЗРАБОТЧИК: 
- Стоимость: 87 500 руб. (полная цена 194 515 руб, скидка 55%).
- Рассрочка: от 4 052 руб./мес.
- Срок обучения: 12 месяцев.
- Программа: Python, Django, FastAPI, базы данных.

2. КУРС ГРАФИЧЕСКИЙ ДИЗАЙНЕР: 
- Стоимость: 105 400 руб. (полная цена 201 754 руб, скидка 48%).
- Рассрочка: от 3 082 руб./мес.
- Срок обучения: 8 месяцев.
- Программа: Дизайн и коммуникации, Photoshop, Illustrator.

3. КУРС ТЕСТИРОВЩИК (QA): 
- Стоимость: 54 400 руб. (полная цена 109 830 руб, скидка 50%).
- Рассрочка: от 2 516 руб./мес.
- Срок обучения: 7 месяцев.
- Программа: Ручное и автоматизированное тестирование.

ОБЩЕЕ: Помощь в трудоустройстве, диплом о переподготовке, налоговый вычет 13%.
"""

# Мульти-клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐍 Python-разработчик"), KeyboardButton(text="🎨 Графический дизайнер")],
        [KeyboardButton(text="🔍 Тестировщик (QA)"), KeyboardButton(text="💳 Скидки и оплата")],
        [KeyboardButton(text="📅 Когда старт?")]
    ],
    resize_keyboard=True
)

def ask_eva(user_id: int, question: str, user_name: str) -> str:
    if user_id not in user_history:
        user_history[user_id] = []

    # Твой промпт без изменений
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
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_history[user_id][-6:])
    messages.append({"role": "user", "content": question})

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages, temperature=0.2, model="llama-3.3-70b-versatile"
        )
        answer = chat_completion.choices[0].message.content.strip()
        user_history[user_id].append({"role": "user", "content": question})
        user_history[user_id].append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return "Уточняю информацию по курсам, секунду..."

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_history[message.from_user.id] = []
    await message.answer("Привет! Я Ева. Выберите направление или задайте вопрос.", reply_markup=main_kb)

@dp.message()
async def handle_message(message: types.Message):
    msg = ask_eva(message.from_user.id, message.text, message.from_user.first_name)
    await message.answer(msg)

flask_app = Flask(__name__)
@flask_app.route('/health')
def health(): return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(dp.start_polling(bot))
