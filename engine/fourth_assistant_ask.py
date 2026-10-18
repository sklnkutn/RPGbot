import os
import json
from dotenv import load_dotenv
from services.loaders import load_character_data, load_prompt
from services.server_request import get_server_url, send_http_post
from services.db import get_character_full_state, update_character_turn_state

#Значениие макс мин изменения переменной
load_dotenv()
RELATION_STEP = int(os.getenv("RELATION_STEP", 5))

async def fourth_assistant_ask(session_id: int, active_char_id: str | None, narrator_text: str, image_prompt: str, model_name: str) -> dict:
    """
    Анализирует последствия сцены для активного персонажа:
    сдвиг отношений на шаг RELATION_STEP, проверка смены одежды и ухода со сцены.
    """
    #Отработка ошибочного запроса
    if not active_char_id:
        return {}
    #Входящие данные
    base_system_prompt = load_prompt("evaluator_prompt.yaml")
    char_yaml = load_character_data(active_char_id)
    char_db = await get_character_full_state(session_id, active_char_id)

    char_info = (
        f"\n\n# Оцениваемый персонаж: {char_yaml.get('name')}\n"
        f"- Характер: {', '.join(char_yaml.get('bio', {}).get('personality_traits', []))}\n"
        f"- Текущая одежда в базе: {char_db.get('current_clothing', 'не указана')}\n"
    )

    #сделать запрос
    #JSON Schema: дискретные сдвиги [-1, 0, 1], проверка одежды и ухода
    evaluator_schema = {
        "relation_shifts": {
            "type": "object",
            "properties": {
                "trust": {"type": "integer", "enum": [-1, 0, 1]},
                "respect": {"type": "integer", "enum": [-1, 0, 1]},
                "affection": {"type": "integer", "enum": [-1, 0, 1]},
                "annoyance": {"type": "integer", "enum": [-1, 0, 1]},
                "fear": {"type": "integer", "enum": [-1, 0, 1]},
                "jealousy": {"type": "integer", "enum": [-1, 0, 1]}
            },
            "required": ["trust", "respect", "affection", "annoyance", "fear", "jealousy"]
        },
        "clothing_changed": {
            "type": "boolean"
        },
        "new_clothing": {
            "type": ["string", "null"]
        },
        "leaves_scene": {
            "type": "boolean"
        }
    }
    
    user_payload = (
        f"[ТЕКСТ НАРРАТОРА]:\n{narrator_text}\n\n"
        f"[ВИЗУАЛЬНЫЙ ПРОМПТ СЦЕНЫ]:\n{image_prompt}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_payload}
    ]
    payload = {
        "model": model_name,
        "messages": messages,
        "format": {
            "type": "object",
            "properties": evaluator_schema,
            "required": ["relation_shifts", "clothing_changed", "new_clothing", "leaves_scene"]
        },
        "stream": False,
        "options": {
            "temperature": 0.1,  # Строгий режим оценщика
            "num_ctx": 2048
        }
    }
    #Запрос к Ollama
    url = get_server_url("ollama", "api/chat")
    response = await send_http_post(url, payload, server="ollama")
    
    if isinstance(response, str):
        print(f"[Fourth Step Error]: {response}")
        return {}
    content = response.get("message", {}).get("content", "")
    #распарсить ответ
    try:
        data = json.loads(content)
        shifts = data.get("relation_shifts", {})    
    #Перевод дискретных шагов [-1, 0, 1] в реальные числовые дельты: delta = shift * RELATION_STEP
        deltas = {stat: shifts.get(stat, 0) * RELATION_STEP for stat in shifts}
        clothing_changed = data.get("clothing_changed", False)
        new_clothing = data.get("new_clothing") if clothing_changed else None
        leaves_scene = data.get("leaves_scene", False)
    #Атомарно обновляем состояние персонажа в SQLite
        await update_character_turn_state(
            session_id=session_id,
            character_id=active_char_id,
            deltas=deltas,
            new_clothing=new_clothing,
            leaves_scene=leaves_scene
        )
        return data
    except Exception as e:
        print(f"[Fourth Step Warning] Ошибка применения изменений состояния: {e}")
        return {}
