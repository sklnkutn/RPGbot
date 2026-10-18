from services.db import save_message
from services.loaders import load_prompt, get_adventure_world_info
from services.server_request import get_server_url, send_http_post

def build_chat_payload(adventure_id: str, model_name: str = "llama3") -> dict:
    """
    1. Формирует тело запроса (payload) для Ollama /api/chat.
    Загружает системный промпт, обогащает его данными мира и добавляет стартовое сообщение.
    """
    # Загружаем базовый системный промпт из файла
    base_system_prompt = load_prompt("first_run_prompt.yaml")
    
    # Получаем параметры мира для конкретного приключения (предполагается, что функция доступна в контексте)
    world_info = get_adventure_world_info(adventure_id)
    
    genres = world_info.get("genre", [])     # Список жанров
    rules = world_info.get("rules", "")       # Правила мира
    
    # Превращаем жанры в строку
    genres_str = ", ".join(genres) if isinstance(genres, list) else str(genres)

    # Дополняем системный промпт контекстом мира
    system_prompt = (
        f"{base_system_prompt}\n\n"
        f"# Контекст текущего мира\n"
        f"- Жанр: {genres_str}\n"
        f"- Правила и особенности мира:\n{rules}"
    )

    # Возвращаем готовый словарь пейлоада для Ollama
    return {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": "[СИСТЕМНОЕ СОБЫТИЕ]: Инициализировать игровую сессию и сгенерировать стартовую сцену согласно правилам."
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 4096
        }
    }

async def first_run(session_id: int, adventure_id: str, model_name: str = "llama3") -> str:
    """
    2. Выполняет запрос: собирает payload, вычисляет URL через ваш модуль 
    и отправляет POST-запрос через send_http_post.
    """
    # Шаг 1. Генерируем пейлоад с помощью первой функции
    payload = build_chat_payload(adventure_id, model_name)
    
    # Шаг 2. Получаем правильный URL через ваш хелпер из server_request.py
    url = get_server_url("ollama", "api/chat")
    
    # Шаг 3. Отправляем запрос с помощью вашей готовой функции send_http_post
    response = await send_http_post(url, payload, server="ollama")
    
    # Шаг 4. Обрабатываем ответ
    # Если send_http_post вернул строку (значит, произошла ошибка сети или таймаут)
    if isinstance(response, str):
        raise RuntimeError(f"Не удалось инициализировать сессию: {response}")
        
    # Извлекаем текст ответа ассистента (Гейммастера)
    assistant_message = response.get("message", {}).get("content", "")
    
    if not assistant_message:
        raise ValueError("Ollama вернула пустой ответ при инициализации сессии.")
        
    # Шаг 5. Сохраняем первый ответ модели в базу данных
    # sender="assistant" (или "gm" / "model" — в зависимости от вашей логики в БД)
    await save_message(
        session_id=session_id,
        sender="assistant",
        text=assistant_message,
        image_path=None,  # Картинку для старта пока не генерируем
        character_id=None,
    )
    
    return assistant_message