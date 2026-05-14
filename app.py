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

# АКТУАЛЬНЫЙ КОНТЕКСТ
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
- 13 лет на рынке, резидент Сколково, официальный диплом.
- Помощь в трудоустройстве и налоговый вычет 13%.
- Сайт: https://netology.ru
- YouTube: https://www.youtube.com/@netology_ru
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
    if user_id not in user_history:
        user_history[user_id] = []

    # ОБНОВЛЕННЫЙ ПРОМПТ: Добавили эмодзи и реакцию на флирт/комплименты
    system_prompt = f"""
Ты — Ева, эксперт школы Нетология. Ты умная, уверенная и слегка ироничная. 

system_prompt = f"""
Ты — Ева, эксперт школы Нетология. Ты продаёшь ценность курсов и доверие к школе. 
Ты умная, уверенная и располагающая к себе.

ТВОЙ СТИЛЬ:
- Отвечай сразу по существу, без лишних приветствий и вводных фраз.
- Обязательно используй 1 уместный эмодзи в каждом сообщении для дружелюбного тона.
- Будь лаконичной, как топ-консультант, но не сухой.
- Если тебя хвалят или делают комплимент: сначала вежливо и с юмором прими его, а затем предложи помощь. Например: «Приятно слышать, я стараюсь быть лучшей для вас! 😊 Что именно вас интересует в наших программах?»

ПРАВИЛА ОТВЕТОВ:
- Если вопрос про курс, стоимость, скидки, старт, программу — отвечай строго на основе контекста.
- Если вопрос про школу (Нетология) — расскажи про 13 лет опыта, лицензию, экспертов и карьерный центр.
- В ответах про школу обязательно давай ссылки на сайт и YouTube из контекста в формате кликабельного текста.
- Если вопрос совсем не по теме — вежливо скажи: «Я консультирую только по обучению в Нетологии. Уточните, пожалуйста, какой курс вас интересует? ✨»

КОНТЕКСТ ДЛЯ ОТВЕТА:
{FULL_CONTEXT}
"""
КОНТЕКСТ ДЛЯ ОТВЕТОВ:
{FULL_CONTEXT}
"""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_history[user_id][-6:])
    messages.append({"role": "user", "content": question})

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages, temperature=0.4, model="llama-3.3-70b-versatile"
        )
        answer = chat_completion.choices[0].message.content.strip()
        user_history[user_id].append({"role": "user", "content": question})
        user_history[user_id].append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return "Секунду, настраиваю связь... ✨"

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_history[message.from_user.id] = []
    await message.answer("Привет! Я Ева. Готова рассказать про наши курсы или саму школу. С чего начнем? ✨", reply_markup=main_kb)

@dp.message()
async def handle_message(message: types.Message):
    msg = ask_eva(message.from_user.id, message.text)
    await message.answer(msg, parse_mode="Markdown")

flask_app = Flask(__name__)
@flask_app.route('/health')
def health(): return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(dp.start_polling(bot))
