import aiosqlite
from services.states import GameStates
from services.loaders import load_characters

DB_NAME = "data.db"

async def init_db():
    """Инициализация/создание базы данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON;") #Включение поддержки внешних ключей в SQLite

        # Таблица игровых сессий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL DEFAULT 'in_progress',
                adventure_id TEXT NOT NULL,
                llm_model TEXT NOT NULL,
                comfy_model TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица персонажей, участвующих в конкретной сессии (с динамическими параметрами)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                character_id TEXT NOT NULL,
                character_status TEXT NOT NULL DEFAULT 'inactive',
                trust INTEGER DEFAULT 0,
                respect INTEGER DEFAULT 0,
                affection INTEGER DEFAULT 0,
                annoyance INTEGER DEFAULT 0,
                fear INTEGER DEFAULT 0,
                jealousy INTEGER DEFAULT 0,
                about_player TEXT DEFAULT '[]',
                about_world TEXT DEFAULT '[]',
                about_others TEXT DEFAULT '[]',
                about_self TEXT DEFAULT '[]',
                current_clothing TEXT DEFAULT '[]',
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        await db.commit()

async def create_session(adventure_id: str, llm_model: str, comfy_model: str, character_ids: list[str]) -> int:
    """Создание новой игровой сессии, привязка персонажей и возвращение ID сессии"""
    
    all_characters = load_characters() # Загрузка персонажей из YAML
    char_dict = {char.get("id"): char for char in all_characters}
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON;")

        #создание сессии со статусом IN_PROGRESS
        cursor = await db.execute("""
            INSERT INTO sessions (state, adventure_id, llm_model, comfy_model)
            VALUES (?, ?, ?, ?)
        """, (GameStates.IN_PROGRESS, adventure_id, llm_model, comfy_model))
        
        session_id = cursor.lastrowid

        # Привязка выбранных персонажей к открываемой сессии
        for char_id in character_ids:
            char_data = char_dict.get(char_id, {}) #поиск персонажа в загруженных YAML-данных
            default_clothing = char_data.get("visual", {}).get("default_clothing", "") #Загрузка дефолтной одежды
            await db.execute("""
                INSERT INTO session_characters (session_id, character_id, current_clothing)
                VALUES (?, ?, ?)
            """, (session_id, char_id, default_clothing))

        await db.commit()
        return session_id

async def save_message(session_id: int, sender: str, text: str, image_path: str = None):
    """Сохранение сообщения в историю диалога сессии"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO messages (session_id, sender, text, image_path)
            VALUES (?, ?, ?, ?)
        """, (session_id, sender, text, image_path))
        await db.commit()

async def get_session_messages(session_id: int):
    """Получение всей истории сообщений для конкретной сессии"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sender, text, image_path, created_at 
            FROM messages 
            WHERE session_id = ? 
            ORDER BY id ASC
        """, (session_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

def _get_last_messages(all_messages: list) -> tuple[str | None, str | None]:
    """
    Вспомогательная функция: последние два сообщения. Возвращает кортеж: (last_assistant_text, last_user_text)
    """
    last_assistant_msg = None
    last_user_msg = None

    # Проходим по истории с конца (в обратном порядке)
    for msg in reversed(all_messages):
        if msg["sender"] == "assistant" and not last_assistant_msg:
            last_assistant_msg = msg["text"]
        elif msg["sender"] == "user" and not last_user_msg:
            last_user_msg = msg["text"]
        
        # Если нашли оба — прекращаем поиск для оптимизации
        if last_assistant_msg and last_user_msg:
            break
            
    return last_assistant_msg, last_user_msg

async def get_session_characters_list(session_id: int) -> list[str]:
    """Временная функция получения списка ID персонажей сессии"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT character_id FROM session_characters WHERE session_id = ?
        """, (session_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row["character_id"] for row in rows]

async def get_active_session_characters(session_id: int) -> list[str]:
    """Отбор активного персонажа из бд"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # Обрати внимание: используем AND и передаем оба параметра в кортеже!
        async with db.execute("""
            SELECT character_id 
            FROM session_characters 
            WHERE session_id = ? AND character_status = ?
        """, (session_id, "active")) as cursor:
            rows = await cursor.fetchall()
            return [row["character_id"] for row in rows]

async def get_session_info(session_id: int) -> dict:
    """Получает информацию о сессии (adventure_id, llm_model и т.д.)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT adventure_id, llm_model, comfy_model, state 
            FROM sessions 
            WHERE id = ?
        """, (session_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {}

async def update_character_status(session_id: int, character_id: str, status: str):
    """Обновляет статус персонажа (например, 'active' или 'inactive') в сессии"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE session_characters 
            SET character_status = ? 
            WHERE session_id = ? AND character_id = ?
        """, (status, session_id, character_id))
        await db.commit()