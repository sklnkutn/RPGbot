import aiosqlite
import json
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
                character_id TEXT,
                is_summarized INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        await db.commit()

        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                chunk_order INTEGER NOT NULL,
                start_message_id INTEGER NOT NULL,
                end_message_id INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
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

async def save_message(session_id: int, sender: str, text: str, image_path: str = None, character_id: str | None):
    """Сохранение сообщения в историю диалога с привязкой к активному персонажу"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO messages (session_id, sender, text, image_path, character_id)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, sender, text, image_path, character_id))
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

async def get_recent_session_messages(session_id: int, limit: int = 10) -> list[dict]:
    """Получает последние N сообщений сессии в хронологическом порядке."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sender, text 
            FROM (
                SELECT id, sender, text 
                FROM messages 
                WHERE session_id = ? 
                ORDER BY id DESC 
                LIMIT ?
            )
            ORDER BY id ASC
        """, (session_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_character_full_state(session_id: int, character_id: str) -> dict:
    """Получение переменных персонажа для запроса по ID-сессии"""    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT character_status, 
                   trust, respect, affection, annoyance, fear, jealousy,
                   about_player, about_world, about_others, about_self, 
                   current_clothing
            FROM session_characters 
            WHERE session_id = ? AND character_id = ?
        """, (session_id, character_id)) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return {}
            
            # Превращаем результат в обычный словарь
            state = dict(row)
            
            # Безопасно десериализуем JSON-поля памяти и одежды из строк в списки/объекты Python
            for field in ["about_player", "about_world", "about_others", "about_self"]:
                try:
                    val = state.get(field)
                    state[field] = json.loads(val) if val else []
                except json.JSONDecodeError:
                    state[field] = []
            state["current_clothing"] = state.get("current_clothing") or ""       
            return state

async def get_session_summaries(session_id: int) -> list[dict]:
    """Получает все сохраненные саммари (архив сюжета) для сессии по порядку."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT chunk_order, summary_text 
            FROM session_summaries 
            WHERE session_id = ? 
            ORDER BY chunk_order ASC
        """, (session_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_unsummarized_messages(session_id: int) -> list[dict]:
    """Получает только те сообщения, которые еще не были упакованы в саммари (is_summarized = 0)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, sender, text 
            FROM messages 
            WHERE session_id = ? AND is_summarized = 0 
            ORDER BY id ASC
        """, (session_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_character_turn_state(session_id: int, character_id: str, deltas: dict[str, int], new_clothing: str | None, leaves_scene: bool):
    """Применяет дельты отношений, обновляет одежду и переключает статус при уходе со сцены."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT trust, respect, affection, annoyance, fear, jealousy, current_clothing
            FROM session_characters 
            WHERE session_id = ? AND character_id = ?
        """, (session_id, character_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return

        def clamp(current_val, delta):
            return max(-100, min(100, (current_val or 0) + (delta or 0)))

        new_trust = clamp(row["trust"], deltas.get("trust", 0))
        new_respect = clamp(row["respect"], deltas.get("respect", 0))
        new_affection = clamp(row["affection"], deltas.get("affection", 0))
        new_annoyance = clamp(row["annoyance"], deltas.get("annoyance", 0))
        new_fear = clamp(row["fear"], deltas.get("fear", 0))
        new_jealousy = clamp(row["jealousy"], deltas.get("jealousy", 0))

        # Если одежда изменилась, пишем новую, иначе сохраняем текущую
        final_clothing = new_clothing.strip() if new_clothing else row["current_clothing"]
        
        # Если персонаж покинул сцену — переводим статус в inactive
        new_status = "inactive" if leaves_scene else "active"

        await db.execute("""
            UPDATE session_characters
            SET trust = ?, respect = ?, affection = ?, annoyance = ?, fear = ?, jealousy = ?,
                current_clothing = ?, character_status = ?
            WHERE session_id = ? AND character_id = ?
        """, (
            new_trust, new_respect, new_affection, new_annoyance, new_fear, new_jealousy,
            final_clothing, new_status,
            session_id, character_id
        ))
        await db.commit()

async def get_chunk_for_summarization(session_id: int, chunk_size: int) -> list[dict]:
    """Возвращает первые chunk_size несуммированных сообщений."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, sender, text, character_id 
            FROM messages 
            WHERE session_id = ? AND is_summarized = 0 
            ORDER BY id ASC 
            LIMIT ?
        """, (session_id, chunk_size)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def mark_messages_as_summarized(message_ids: list[int]):
    """Помечает упакованные сообщения флагом is_summarized = 1."""
    if not message_ids:
        return
    placeholders = ",".join("?" for _ in message_ids)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"""
            UPDATE messages 
            SET is_summarized = 1 
            WHERE id IN ({placeholders})
        """, message_ids)
        await db.commit()

async def save_session_summary_chunk(session_id: int, start_msg_id: int, end_msg_id: int, summary_text: str):
    """Сохраняет готовый фрагмент суммаризации сюжета в session_summaries."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Определяем следующий номер чанка
        async with db.execute("SELECT COUNT(*) FROM session_summaries WHERE session_id = ?", (session_id,)) as cursor:
            count = (await cursor.fetchone())[0]
            next_order = count + 1

        await db.execute("""
            INSERT INTO session_summaries (session_id, chunk_order, start_message_id, end_message_id, summary_text)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, next_order, start_msg_id, end_msg_id, summary_text))
        await db.commit()

async def append_character_memories(session_id: int, character_id: str, new_facts: dict):
    """Добавляет новые уникальные факты в списки памяти персонажа."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT about_player, about_world, about_self, about_others 
            FROM session_characters 
            WHERE session_id = ? AND character_id = ?
        """, (session_id, character_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return

        def update_list(field_name):
            try:
                existing = json.loads(row[field_name]) if row[field_name] else []
            except Exception:
                existing = []
            for item in new_facts.get(field_name, []):
                if item and item not in existing:
                    existing.append(item)
            return json.dumps(existing, ensure_ascii=False)

        await db.execute("""
            UPDATE session_characters 
            SET about_player = ?, about_world = ?, about_self = ?, about_others = ?
            WHERE session_id = ? AND character_id = ?
        """, (
            update_list("about_player"),
            update_list("about_world"),
            update_list("about_self"),
            update_list("about_others"),
            session_id, character_id
        ))
        await db.commit()