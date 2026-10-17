import json
from services.loaders import load_character_data, load_prompt_section
from services.server_request import get_server_url, send_http_post
from services.db import get_character_full_state, update_character_clothing  # нужно добавить в db.py

async def third_assistant_ask(session_id: int, active_char_id: str | None, narrator_text: str, model_name: str) -> dict:
    """
    Генерирует визуальный промпт для ComfyUI на основе последнего ответа нарратора.
    Возвращает dict: {"positive_prompt": str, "clothing_update": str | None}
    """

    #выбор базового промпта в зависимости от того есть ли активный персонаж
    #Необходимо создание форматированное сообщения как от ассистента последний ответ от нарратора
    #(не знаю как лучше через сохранение в бд-потом придется переписывать чтобы добавить ссылку на картинку для рендера,
    #возможно стоит сначала полностью обработать в цикле и только после сохранить с сылкой)
    #и добавить текущее одеяние персонажа, дефолтное одеяние как опцию и базовый промпт обязательный к употреблению, при это только если активный персонаж
    # 1. Формируем контекст персонажа (если он на сцене)
    if active_char_id:
        base_system_prompt = load_prompt_section("visual_assistant_prompt.yaml", "prompt_with_char")
        char_yaml = load_character_data(active_char_id)
        char_db = await get_character_full_state(session_id, active_char_id)
        
        char_name = char_yaml.get("name", "Character")
        base_visual = char_yaml.get("visual", {}).get("base_prompt", "")
        current_clothing = char_db.get("current_clothing", "")
        
        char_context = (
            f"\n\n# Персонаж в кадре:\n"
            f"- Имя: {char_name}\n"
            f"- Базовые визуальные теги: {base_visual}\n"
            f"- Текущая одежда: {current_clothing}\n"
        )
    else:
        base_system_prompt = load_prompt_section("visual_assistant_prompt.yaml", "prompt_without_char")
        char_context = "\n\n# В кадре НЕТ персонажей. Это пейзаж, окружение или вид от первого лица (POV)."
    system_prompt = f"{base_system_prompt}{char_context}"
    #Можно через shema сделать промпт разносоставным, чтобы вытащить текущую одежду отдельно, но потом нужно пересобрать ответ из частей, или заставить переписать отдельно, но shema похоже не избежать
    #Но если персонажа нет то shema не нужен вообще
    # 2. JSON Schema для строгого ответа
    visual_schema = {
        "positive_prompt": {
            "type": "string",
            "description": "Теги для генератора изображений на английском через запятую (локация, атмосфера, поза, свет, детали)."
        },
        "clothing_update": {
            "type": ["string", "null"],
            "description": "Если одежда персонажа изменилась в этой сцене, указать новый комплект на английском. Иначе null."
        }
    }

    # 3. Единственное сообщение пользователя — это свежая реплика Нарратора
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"[ОПИСАНИЕ СЦЕНЫ ДЛЯ ВИЗУАЛИЗАЦИИ]:\n{narrator_text}"}
    ]
    payload = {
        "model": model_name,
        "messages": messages,
        "format": {
            "type": "object",
            "properties": visual_schema,
            "required": ["positive_prompt", "clothing_update"]
        },
        "stream": False,
        "options": {
            "temperature": 0.3,  # Для промптов лучше низкая температура (меньше галлюцинаций)
            "num_ctx": 2048
        }
    }
    #отправка запроса
    url = get_server_url("ollama", "api/chat")
    response = await send_http_post(url, payload, server="ollama")
    if isinstance(response, str):
        raise RuntimeError(f"Ошибка вызова visual assistant: {response}")
    content = response.get("message", {}).get("content", "")
    
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Fallback, если модель выдала неидеальный JSON
        parsed = {
            "positive_prompt": "masterpiece, best quality, cinematic view, atmospheric lighting",
            "clothing_update": None
        }

    # 4. Если на сцене есть персонаж — приклеиваем обязательные теги внешности
    if active_char_id:
        clothing_to_use = parsed.get("clothing_update") or current_clothing
        
        # Если одежда изменилась — сохраняем новое состояние в БД
        if parsed.get("clothing_update") and parsed.get("clothing_update") != current_clothing:
            await update_character_clothing(session_id, active_char_id, parsed["clothing_update"])
            
        full_positive = f"{base_visual}, {clothing_to_use}, {parsed.get('positive_prompt', '')}"
    else:
        full_positive = parsed.get("positive_prompt", "")
    return {
        "positive_prompt": full_positive,
        "raw_scene_prompt": parsed.get("positive_prompt", "")
    }