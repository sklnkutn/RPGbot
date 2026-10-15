from services.db import save_message, get_session_messages, get_session_info, get_active_session_characters
from engine.first_assistant_ask import first_assistant_ask

get_active_session_characters

async def process_player_turn(session_id: int, user_text: str) -> str:
    """
    Обработка хода игрока: интеграция первого шага (анализ сообщения через first_assistant_ask).
    """
    # 1. Сохраняем сообщение игрока в историю базы данных
    await save_message(session_id=session_id, sender="user", text=user_text)

    # 2. Получаем параметры сессии (в частности, adventure_id и выбранную модель LLM)
    session_info = await get_session_info(session_id)
    adventure_id = session_info.get("adventure_id")
    llm_model = session_info.get("llm_model")
    comfy_model = session_info.get("comfy_model")
    
    try:
        # Проверяем, есть ли уже активные персонажи на сцене
        active_chars = await get_active_session_characters(session_id)
        
        if active_chars:
            print(f"[Pipeline] Найден активный персонаж: {active_chars}. Пропускаем Шаг 1.")
            # В будущем здесь будет вызов второго шага (генерация сюжета)
            assistant_message = f"[Pipeline]: Персонаж {active_chars} уже на сцене. Ожидаем генерацию ответа..."
        else:
            print("[Pipeline] Активных персонажей нет. Запускаем Шаг 1 (анализ).")
            response_data = await first_assistant_ask(
                session_id=session_id,
                adventure_id=adventure_id,
                user_text=user_text,
                model_name=llm_model
            )
            assistant_message = str(response_data)

    except Exception as e:
        assistant_message = f"[Ошибка в конвейере хода]: {e}"
        print(f"[Pipeline Error]: {e}")

    return assistant_message