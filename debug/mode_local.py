# debug/mode_local.py
import json

def get_local_ollama_models():
    return {
        "models": [
            {"name": "llama3:8b"},
            {"name": "mistral:7b"},
            {"name": "gemma2:9b"}
        ]
    }

def get_local_comfy_models():
    return [
        "WAI-illustrious-SDXL_16.safetensors",
        "nova_furry.safetensors",
        "illustmix.safetensors"
    ]

def generate_smart_ollama_response(payload: dict) -> dict:
    """
    Автоматически распознает, какой шаг движка вызвал Ollama, 
    и возвращает соответствующий корректный ответ (валидный JSON или текст).
    """
    messages = payload.get("messages", [])
    format_schema = payload.get("format", {})
    properties = format_schema.get("properties", {}) if isinstance(format_schema, dict) else {}
    
    system_text = messages[0].get("content", "") if messages else ""
    user_text = messages[-1].get("content", "") if messages else ""

    # 1. Шаг 1 (First Ask): проверка необходимости активации персонажа
    if "need_new_character" in properties:
        char_enum = properties.get("characters_name", {}).get("enum", ["char_black_widow"])
        chosen_char = char_enum[0] if char_enum else "char_black_widow"
        content = json.dumps({
            "need_new_character": True,
            "characters_name": chosen_char
        }, ensure_ascii=False)

    # 2. Шаг 4 (Fourth Ask): оценка сдвига статов, одежды и ухода
    elif "relation_shifts" in properties:
        content = json.dumps({
            "relation_shifts": {
                "trust": 1,
                "respect": 1,
                "affection": 0,
                "annoyance": 0,
                "fear": 0,
                "jealousy": 0
            },
            "clothing_changed": False,
            "new_clothing": None,
            "leaves_scene": False
        }, ensure_ascii=False)

    # 3. Шаг 5А (Fifth Ask): извлечение долговременной памяти
    elif "about_player" in properties:
        content = json.dumps({
            "about_player": ["Игрок действует решительно и осторожно"],
            "about_world": ["Остров хранит следы квантовой катастрофы"],
            "about_self": ["Не привыкла доверять незнакомцам"]
        }, ensure_ascii=False)

    # 4. Шаг 3 (Third Ask): генератор визуального промпта
    elif "image prompt generator" in system_text.lower() or "visual tags" in system_text.lower():
        content = "1girl, black widow, marvel, red hair, black bodysuit, sitting by campfire, beach, night, cinematic lighting, masterpiece, 8k"

    # 5. Шаг 5Б (Fifth Ask): суммаризация чанка
    elif "летописец" in system_text.lower() or "chunk_summary" in system_text.lower():
        content = "Игрок исследовал береговую линию, нашел остатки лагеря и наладил контакт со спутником."

    # 6. First Run: инициализация игры
    elif "[СИСТЕМНОЕ СОБЫТИЕ]" in user_text:
        content = "Холодный прибой с шумом накатывает на песчаный берег. Вы приходите в себя возле обломков шлюпки; вокруг темнеют непроходимые заросли неизвестного острова."

    # 7. Шаг 2 (Second Ask): основной ответ Нарратора
    else:
        content = "Вы осторожно делаете шаг вперед. В зарослях неподалеку слышится шорох, и Наташа мгновенно настораживается, кладя руку на рукоять оружия: «Тише. Мы здесь не одни»."

    return {
        "model": payload.get("model", "llama3:8b"),
        "message": {
            "role": "assistant",
            "content": content
        },
        "done": True
    }