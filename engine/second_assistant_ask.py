import os
import json
from engine.map_relation_to_text import map_relation_to_text
from services.loaders import get_adventure_world_info, load_character_data, load_prompt_section
from services.server_request import get_server_url, send_http_post
from services.db import get_character_full_state, get_session_summaries, get_unsummarized_messages

async def second_assistant_ask(
    session_id: int,
    adventure_id: str,
    active_char_id: str | None,
    model_name: str,
    user_text: str,
) -> str:
    # 1. Загрузка параметров мира
    world_info = get_adventure_world_info(adventure_id)
    genres_str = ", ".join(world_info.get("genre", []))
    rules = world_info.get("rules", "")
    # 2. Выбор промпта и сборка блока персонажа
    if active_char_id:
        base_prompt = load_prompt_section("narrator_prompt.yaml", "prompt_with_char")
        char_yaml = load_character_data(active_char_id)
        char_db = await get_character_full_state(session_id, active_char_id)
        
        #Словарь перевода переменных персонажа для чистого русскоязычного промпта
        stat_names_ru = {
            "trust": "Доверие",
            "respect": "Уважение",
            "affection": "Привязанность",
            "annoyance": "Раздражение",
            "fear": "Страх",
            "jealousy": "Ревность"
        }
        # Преобразование статов в текст
        relations_desc = "\n".join([
            f"- {stat_names_ru.get(stat, stat)}: {map_relation_to_text(stat, char_db.get(stat, 0))}"
            for stat in ["trust", "respect", "affection", "annoyance", "fear", "jealousy"]
        ])
        
        knowledge_blocks = []
        
        know_player = char_db.get("about_player", [])
        know_world = char_db.get("about_world", [])
        know_others = char_db.get("about_others", [])
        know_self = char_db.get("about_self", [])

        if know_player:
            knowledge_blocks.append(f"- О игроке: {', '.join(know_player)}")
        if know_world:
            knowledge_blocks.append(f"- О мире: {', '.join(know_world)}")
        if know_others:
            knowledge_blocks.append(f"- О других: {', '.join(know_others)}")
        if know_self:
            knowledge_blocks.append(f"- О себе: {', '.join(know_self)}")

        # Проверяем, есть ли вообще хоть какие-то факты
        if knowledge_blocks:
            knowledge_desc = "\n".join(knowledge_blocks)
            knowledge_section = f"- Известные персонажу факты:\n{knowledge_desc}"
        else:
            knowledge_section = "- Известные персонажу факты: пока нет накопленных знаний."

        char_context = (
            f"\n\n# Активный персонаж на сцене:\n"
            f"- Имя: {char_yaml.get('name')} ({char_yaml.get('alias', '')})\n"
            f"- Пол: {char_yaml.get('gender')}\n"
            f"- Возраст: {char_yaml.get('age')}\n"
            f"- Характер: {', '.join(char_yaml.get('bio', {}).get('personality_traits', []))}\n"
            f"- Описание: {char_yaml.get('bio', {}).get('description', '')}\n"
            f"- Отношение к игроку:\n{relations_desc}"
            f"{knowledge_section}"
        )
    else:
        base_prompt = load_prompt_section("narrator_prompt.yaml", "prompt_without_char")
        char_context = "\n\n# Спутники: На данный момент игрок действует в одиночку."

    # 3. Полный системный промпт
    system_prompt = (
        f"{base_prompt}\n\n"
        f"# Контекст мира:\n"
        f"- Жанр: {genres_str}\n"
        f"- Правила мира:\n{rules}"
        f"{char_context}"
    )

    # 4. Сборка истории диалога (Саммари + Несуммированные свежие сообщения)
    
    full_system_prompt = system_prompt  # Здесь твои правила, жанр и описание персонажа

    # Подтягиваем архивные саммари (если они есть) и вшиваем их прямо в систему
    summaries = await get_session_summaries(session_id)
    if summaries:
        history_summary_text = "\n\n# Предыдущие события (Архив):\n" + "\n".join([f"- {s['summary_text']}" for s in summaries])
        full_system_prompt += history_summary_text

    # 2. Создаем массив сообщений с ЕДИНСТВЕННЫМ системным блоком
    formatted_messages = [{
        "role": "system",
        "content": full_system_prompt
    }]

    # Б. Подтягиваем свежие сообщения, которые еще не ушли в архив
    recent_messages = await get_unsummarized_messages(session_id)
    
    for msg in recent_messages:
        role = "user" if msg["sender"] == "user" else "assistant"
        formatted_messages.append({
            "role": role,
            "content": msg["text"]
        })

    formatted_messages.append({
        "role": "user",
        "content": user_text
    })

    #формирование запроса
    payload = {
        "model": model_name,
        "messages": formatted_messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 4096
        }
    }
    #отправка запроса
    url = get_server_url("ollama", "api/chat")
    response = await send_http_post(url, payload, server="ollama")
    if isinstance(response, str):
        raise RuntimeError(f"Сетевая ошибка при запросе нарратора: {response}")
    narrator_text = response.get("message", {}).get("content", "")
    if not narrator_text:
        raise ValueError("Ollama вернула пустой ответ нарратора.")
    return narrator_text