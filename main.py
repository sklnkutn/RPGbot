from dotenv import load_dotenv
from nicegui import app, ui

from db import init_db
from services.llm import ask_llm
from ui.views import setup_routes

load_dotenv() #Загрузка переменных окружения из файла .env
app.add_static_files('/static', 'static')

@app.on_startup #связка с базой данных
async def startup_event():
    await init_db()
    print("База данных инициализирована")

setup_routes()

if __name__ in {"__main__", "__mp_main__"}: #Запуск основного процесса пользователем напрямую
    ui.run(
        title="RPG Adventure Engine",
        port=8080,
        reload=True,
        storage_secret="rpg_secret_key", #хранить переменне сессии
        dark=True    
    )