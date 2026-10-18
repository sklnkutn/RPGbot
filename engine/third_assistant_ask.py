import json
from services.loaders import load_character_data, load_prompt_section
from services.server_request import get_server_url, send_http_post
from services.db import get_character_full_state, get_session_info

async def third_assistant_ask(session_id: int, active_char_id: str | None, narrator_text: str, model_name: str) -> str:
    """Генерирует визуальный промпт для ComfyUI на основе последнего ответа нарратора."""
    session_info = await get_session_info(session_id)
    comfy_model = session_info.get("comfy_model", "Не указана")

    if active_char_id:
        base_system_prompt = load_prompt_section("visual_assistant_prompt.yaml", "prompt_with_char")
        char_yaml = load_character_data(active_char_id)
        char_db = await get_character_full_state(session_id, active_char_id)
        
        visual_data = char_yaml.get("visual", {})
        char_name = char_yaml.get("name", "Character")
        base_visual = visual_data.get("base_prompt", "")
        default_clothing = visual_data.get("default_clothing", "")
        current_clothing = char_db.get("current_clothing", "") or default_clothing
        
        char_context = (
            f"\n\n# Персонаж в кадре:\n"
            f"- Имя: {char_name}\n"
            f"- Базовые визуальные теги: {base_visual}\n"
            f"- Текущая одежда: {current_clothing}\n"
            f"- Базовая одежда (по умолчанию): {default_clothing}\n"
        )
    else:
        base_system_prompt = load_prompt_section("visual_assistant_prompt.yaml", "prompt_without_char")
        char_context = "\n\n# В кадре НЕТ персонажей. Это пейзаж, окружение или вид от первого лица (POV)."
    
    model_context = (f"\n\n# Целевая модель генерации изображений: {comfy_model}.")
    system_prompt = f"{base_system_prompt}{model_context}{char_context}"

    # 3. Единственное сообщение пользователя — это свежая реплика Нарратора
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"[ОПИСАНИЕ СЦЕНЫ ДЛЯ ВИЗУАЛИЗАЦИИ]:\n{narrator_text}"}
    ]
    payload = {
        "model": model_name,
        "messages": messages,
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
    
    raw_prompt = response.get("message", {}).get("content", "").strip()
    
    # Страховка на случай пустого ответа
    if not raw_prompt:
        raw_prompt = "masterpiece, best quality, cinematic lighting, atmospheric"

    return raw_prompt