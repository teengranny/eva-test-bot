import os
from sentence_transformers import SentenceTransformer
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def get_embedding(text):
    return model.encode(text).tolist()

with open("data.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Разбивка по двойным переносам строк (абзацы)
chunks = [p.strip() for p in text.split("\n\n") if p.strip()]

for i, chunk in enumerate(chunks):
    print(f"Загрузка {i+1}/{len(chunks)}")
    supabase.table("documents_free").insert({
        "content": chunk,
        "metadata": {"source": "netology"},
        "embedding": get_embedding(chunk)
    }).execute()

print("✅ Данные загружены в таблицу documents_free")