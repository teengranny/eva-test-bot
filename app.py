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

# Инициализация Groq с таймаутом
http_client = httpx.Client(timeout=30.0)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"), http_client=http_client)
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

# Память бота (ограничим последними 10 сообщениями)
user_history = {}

# Актуальный контекст (данные Нетологии на май 2026)
FULL_CONTEXT = """
1. КУРС PYTHON-РАЗРАБОТЧИК: 
- Стоимость: 87 500 руб. (скидка 55%). Рассрочка: от 4 052 руб./мес.
- Срок: 12 месяцев. Программа: Django, FastAPI, базы данных.

2. КУРС ГРАФИЧЕСКИЙ ДИЗАЙНЕР: 
- Стоимость: 105 400 руб. (скидка 48%). Рассрочка: от 3 082 руб./мес.
- Срок: 8 месяцев. Программа: Photoshop, Illustrator, Figma.

3. КУРС ТЕСТИРОВЩИК (QA): 
- Стоимость: 54 400 руб. (скидка 50%). Рассрочка: от 2 516 руб./мес.
- Срок: 7 месяцев. Программа: Ручное и автотестирование.

ИНФОРМАЦИЯ О ШКОЛЕ (НЕТОЛОГИЯ):
- 13 лет на рынке онлайн-образования. Резидент Сколково.
- Государственная лицензия: выдаем официальный диплом о переподготовке.
- Более 1000 топовых экспертов из бигтеха (Yandex, Ozon, Avito).
- Центр развития карьеры: помогаем с резюме и собеседованиями.
- Официальный сайт: https://netology.ru
- YouTube канал: https://www.youtube.com/@netology_ru
"""

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐍 Python-разработчик"), KeyboardButton(text="🎨 Графический дизайнер")],
        [KeyboardButton(text="🔍 Тестировщик (QA)"), KeyboardButton(text="🏫 О Нетологии")],
        [KeyboardButton(text="💳 Скидки и оплата"), KeyboardButton(text="📅 Когда старт?")]
    ],
    resize_keyboard=True
)

def ask_eva(user_id: int, question: str) -> str:
    # Инициализируем историю, если её нет
    if user_id not in user_history:
        user_history[user_id] = []

    system_prompt = f"""
Ты — Ева, эксперт школы Нетология. Ты продаёшь ценность курсов и доверие к школе.

ТВОЙ СТИЛЬ:
- Отвечай сразу по существу, без лишних приветствий и вводных фраз.
- Используй не более одного смайлика за ответ.
- Будь дружелюбной и лаконичной, как опытный консультант.
- Если тебя хвалят, ответь примерно так: «Это правда сильная программа. Что именно вас интересует?»

ПРАВИЛА ОТВЕТОВ:
- Если вопрос про курс, стоимость, скидки, старт, программу — отвечай строго на основе контекста.
- Если вопрос про школу (Нетология) — расскажи про 13 лет, лицензию, экспертов, карьерный центр.
- В ответах на кнопки «О Нетологии» обязательно давай ссылки на сайт и YouTube (они уже в контексте).
- Если вопрос не по теме обучения — вежливо скажи: «Я консультирую только по курсам Нетологии. Уточните, пожалуйста, какой курс вас интересует?»

ИСПОЛЬЗУЙ ТОЛЬКО ЭТУ ИНФОРМАЦИЮ:
{FULL_CONTEXT}
"""

    # Берём последние 6 сообщений из истории (3 вопроса и 3 ответа) + системный промпт
    history_messages = user_history[user_id][-6:]  # список словарей с role и content
    messages = [{"role": "system", "content": system_prompt}] + history_messages
    messages.append({"role": "user", "content": question})

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            temperature=0.2,
            model="llama-3.3-70b-versatile"
        )
        answer = chat_completion.choices[0].message.content.strip()
        
        # Сохраняем вопрос и ответ в историю (не более 20 сообщений всего)
        user_history[user_id].append({"role": "user", "content": question})
        user_history[user_id].append({"role": "assistant", "content": answer})
        # Ограничиваем историю 20 сообщениями (10 диалогов)
        if len(user_history[user_id]) > 20:
            user_history[user_id] = user_history[user_id][-20:]
        return answer
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return "Секунду, уточняю информацию... Повторите вопрос, пожалуйста."

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_history:
        user_history[user_id] = []
    await message.answer(
        "Привет! Я Ева. Выберите курс или узнайте больше о нашей школе.",
        reply_markup=main_kb
    )

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    answer = ask_eva(user_id, message.text)
    # Разрешаем кликабельные ссылки, отключаем превью для чистоты
    await message.answer(answer, parse_mode="Markdown", disable_web_page_preview=True)

# Flask для healthcheck (чтобы Render не убивал процесс)
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Бот запущен и работает...")
    asyncio.run(dp.start_polling(bot))
