import os
import json
from dotenv import load_dotenv
from services.logger import logger
from services.loaders import load_character_data, load_prompt
from services.server_request import get_server_url, send_http_post
from services.db import get_character_full_state

#Значениие макс мин изменения переменной
load_dotenv()
RELATION_STEP = int(os.getenv("RELATION_STEP", 5))

async def fourth_assistant_ask(session_id: int, active_char_id: str | None, narrator_text: str, image_prompt: str, model_name: str) -> dict:
    """
    Анализирует последствия сцены для активного персонажа:
    сдвиг отношений на шаг RELATION_STEP, проверка смены одежды и ухода со сцены.
    """
    #ID для логгирования
    ctx = f"[Session #{session_id}] [Char: {active_char_id}]"

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
    system_prompt = f"{base_system_prompt}{char_info}"

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
        logger.error(f"{ctx} Ошибка вызова Ollama на Шаге 4: {response}")
        raise RuntimeError(f"Ошибка вызова Ollama на шаге оценки состояния: {response}")
    content = response.get("message", {}).get("content", "")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"{ctx} Невалидный JSON от оценщика: {content}")
        raise ValueError(f"Оценщик вернул невалидный JSON: {content}") from e

    shifts = data.get("relation_shifts")
    if not isinstance(shifts, dict):
        raise ValueError("Оценщик не вернул объект relation_shifts")

    stat_names = ("trust", "respect", "affection", "annoyance", "fear", "jealousy")
    normalized_shifts = {}
    for stat in stat_names:
        value = shifts.get(stat)
        if type(value) is not int or value not in (-1, 0, 1):
            raise ValueError(f"Оценщик вернул недопустимое значение для {stat}: {value!r}")
        normalized_shifts[stat] = value * RELATION_STEP

    clothing_changed = data.get("clothing_changed")
    leaves_scene = data.get("leaves_scene")
    if not isinstance(clothing_changed, bool) or not isinstance(leaves_scene, bool):
        raise ValueError("Оценщик вернул некорректные clothing_changed или leaves_scene")

    new_clothing = data.get("new_clothing")
    if clothing_changed:
        if not isinstance(new_clothing, str) or not new_clothing.strip():
            raise ValueError("Оценщик отметил смену одежды, но не вернул её описание")
        new_clothing = new_clothing.strip()
    else:
        new_clothing = None

    return {
        "deltas": normalized_shifts,
        "new_clothing": new_clothing,
        "leaves_scene": leaves_scene,
    }
