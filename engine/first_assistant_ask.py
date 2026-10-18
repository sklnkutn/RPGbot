import json
from services.db import get_session_messages, get_session_characters_list, _get_last_messages, update_character_status
from services.loaders import get_adventure_world_info, load_characters, load_prompt, load_prompt_section
from services.server_request import get_server_url, send_http_post
from services.states import CharStates
   
async def first_assistant_ask (session_id: int, adventure_id: str, user_text: str, model_name: str) -> str:
    """
    Определение допустимого персонажа по булеву и выбор персонажа из списка
    """
    
    # 1. Получаем информацию о мире и правилах приключения, айди персонажей и их количество
    world_info = get_adventure_world_info(adventure_id)
    genres = ", ".join(world_info.get("genre", []))
    rules = world_info.get("rules", "")
    session_chars = await get_session_characters_list(session_id)
    char_count = len(session_chars)

    #отбор промпта и условий для запроса по количеству персонажей
    if char_count == 1:
        prompt_key = "prompt_single_char"
        required_schema = ["need_new_character"]
        characters_schema = {
            "need_new_character": {
                "type": "boolean"
            }
        }
        active_character = session_chars[0]
    else:
        prompt_key = "prompt_multiple_char"
        required_schema = ["need_new_character", "characters_name"]
        characters_schema = {
            "need_new_character": {
                "type": "boolean"
            },
            "characters_name": {
                "type": "string",
                "enum": session_chars 
            } 
        }

    # 2. Подготавливаем системный промпт с учетом правил мира
    base_system_prompt = load_prompt_section("start_analys_prompt.yaml", prompt_key)
    
    # Превращаем жанры в строку
    genres_str = ", ".join(genres) if isinstance(genres, list) else str(genres)
    
    # Дополняем системный промпт контекстом мира
    system_prompt = (
        f"{base_system_prompt}\n\n"
        f"# Контекст текущего мира\n"
        f"- Жанр: {genres_str}\n"
        f"- Правила и особенности мира:\n{rules}"
    )

    # 3. Загружаем историю сообщений текущей сессии из базы данных
    all_messages = await get_session_messages(session_id)

    #Получение последних двух ответов
    last_assistant_msg, _ = _get_last_messages(all_messages)
    
    # Преобразуем историю из формата БД в формат, который понимает Ollama (список словарей с role и content)
    formatted_messages = [{"role": "system", "content": system_prompt}]

    if last_assistant_msg:
        formatted_messages.append({
            "role": "assistant",
            "content": last_assistant_msg
        })

    # 4. Добавляем текущее новое сообщение игрока в конец истории
    formatted_messages.append({
        "role": "user",
        "content": user_text
    })

     #итоговый payload (тело запроса) для Ollama
    payload = {
        "model": model_name,
        "messages": formatted_messages,
        "format": {
            "type": "object",
            "properties": characters_schema,
            "required": required_schema
        },
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 4096
        }
    }
    # правильный URL через ваш хелпер из server_request.py
    url = get_server_url("ollama", "api/chat")
    
    # Шаг 3. Отправляем запрос функции send_http_post
    response = await send_http_post(url, payload, server="ollama")
    
    # Шаг 4. Обрабатываем ответ
    # Если send_http_post вернул строку (значит, произошла ошибка сети или таймаут)
    if isinstance(response, str):
        raise RuntimeError(f"Не удалось инициализировать сессию: {response}")
        
    # Извлекаем текст ответа ассистента
    assistant_message = response.get("message", {}).get("content", "")
    
    if not assistant_message:
        raise ValueError("Ollama вернула пустой ответ при инициализации сессии.")
    

    try:
        parsed_json = json.loads(assistant_message)
        need_new = parsed_json.get("need_new_character", False)
        target_char = parsed_json.get("characters_name")

        if need_new and not target_char:
            session_chars = await get_session_characters_list(session_id)
            if len(session_chars) == 1:
                target_char = session_chars[0]

        # Единая точка активации статуса в базе данных
        if need_new and target_char:
            await update_character_status(session_id, target_char, CharStates.ACTIVE)
            print(f"[First Step Logic] Персонаж '{target_char}' успешно активирован в сессии #{session_id}.")
        else:
            print(f"[First Step Logic] Новые персонажи не активированы (need_new={need_new}).")
            
    except json.JSONDecodeError:
        print(f"[First Step Warning] Не удалось распарсить JSON от модели: {assistant_message}")

    return assistant_message