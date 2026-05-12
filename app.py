import os
import asyncio
import threading
import logging
from flask import Flask
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer
from groq import Groq
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

load_dotenv()

# ------------------ НАСТРОЙКИ ------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([TELEGRAM_BOT_TOKEN, GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    logging.error("❌ Критическая ошибка: не все переменные окружения заданы!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer('all-MiniLM-L6-v2')
groq_client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ------------------ ЛОГИКА RAG ------------------
def ask_eva(question, user_name="Студент"):
    question_embedding = model.encode(question).tolist()
    
    rpc_params = {
        'query_embedding': question_embedding,
        'match_threshold': 0.25,
        'match_count': 5
    }

    try:
        response = supabase.rpc('match_documents_free', rpc_params).execute()
        data = response.data
        if data:
            context = "\n\n".join([item['content'] for item in data])
        else:
            context = ""
    except Exception as e:
        print(f"[ERROR] Ошибка поиска: {e}")
        context = ""

    system_prompt = f"""
Ты — Ева, куратор онлайн-школы Нетология. Ты разговариваешь с пользователем {user_name}.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе КОНТЕКСТА ниже.
2. Если в КОНТЕКСТЕ НЕТ информации — скажи: 
   "Извините, у меня нет точной информации по этому вопросу. Я передам ваш запрос менеджеру."
3. НЕ используй свои знания, НЕ выдумывай факты.

КОНТЕКСТ:
{context if context else "Контекст пуст."}
"""

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.0,
        model="llama-3.3-70b-versatile"
    )
    return chat_completion.choices[0].message.content

# ------------------ TELEGRAM ХЕНДЛЕРЫ ------------------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я Ева, AI-куратор Нетологии. \nЗадай мне вопрос о курсе Python-разработчик.\n\nПримеры вопросов:\n• Сколько стоит курс?\n• Какая программа обучения?\n• Когда старт?")

@dp.message()
async def handle_question(message: types.Message):
    user_name = message.from_user.first_name
    answer = ask_eva(message.text, user_name)
    await message.answer(answer)

# ------------------ FLASK ДЛЯ HEALTHCHECK ------------------
flask_app = Flask(__name__)

@flask_app.route('/') # Путь по умолчанию
@flask_app.route('/health') # Путь /health
def health_check():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# ------------------ ЗАПУСК ------------------
async def main():
    threads = threading.Thread(target=run_flask, daemon=True)
    threads.start()
    print("✅ Flask сервер для healthcheck запущен в фоне.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
