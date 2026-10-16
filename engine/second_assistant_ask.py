from dotenv import load_dotenv
from services.loaders import get_adventure_world_info, load_characters, load_prompt, load_prompt_section
from services.server_request import get_server_url, send_http_post

load_dotenv() #Загрузка переменных окружения из файла .env
MIN_MESSAGE_COUNT = int(os.getenv("MAX_MESSAGE_COUNT", 20))
MAX_MESSAGE_COUNT_BEFORE_SUMM = int(os.getenv("MAX_MESSAGE_COUNT_BEFORE_SUMM", 20))


async def second_assistant_ask (session_id: int, adventure_id: str, user_text: str, model_name: str) -> dict:

    #Взятие переменных
    world_info = get_adventure_world_info(adventure_id)
    genres = ", ".join(world_info.get("genre", []))
    rules = world_info.get("rules", "")
    #session_chars = await get_session_characters_list(session_id) - сделать новую функцию, нужен активный персонаж если есть
    base_system_prompt = load_prompt_section("narrator_prompt.yaml", prompt_key)
    #Формируем системный промпт нарратора
    # Превращаем жанры в строку
    genres_str = ", ".join(genres) if isinstance(genres, list) else str(genres)

    #
    #
    #отбор последних Х сообщений
    messages_count = 
        #если меньше максимума вернуть все
        if messages_count < MAX_MESSAGE_COUNT_BEFORE_SUMM
            message_history = all_messages #сделать функцию вытащить все сообщения
        #если больше максимума, то минимальное количество + количество сообщений между сжатиями(новая переменная в бд? счетчик в конце цикла?)
    #Добавить функцию взять последние Х сообщений из бд

    #определить есть ли активный персонаж в бд, если есть то вытащить ID

    #если есть вытащить его характер и био из YAML, вытащить текущие переменные
    
    #Изменить числовые переменные в рамках от -100 до +100 в понятные модели семантическое значение(скорее всего отдельная функция, как приравнять?)

    # Дополняем системный промпт контекстом мира
    system_prompt = (
        f"{base_system_prompt}\n\n"
        f"# Контекст текущего мира\n"
        f"- Жанр: {genres_str}\n"
        f"- Правила и особенности мира:\n{rules}"
    )    
    #Создание форматированных ответов от количества персонажей р

    #формирование запроса
    payload = {
        "model": model_name,
        "messages": formatted_messages,
        "stream": False,
        "format": {
            "type": "object",
            "narrator_answer": "str"
        },
        "options": {
            "temperature": 0.7,
            "num_ctx": 4096
        }
    }
    #отправка запроса
    url = get_server_url("ollama", "api/chat")
    try:
        response = await send_http_post(url, payload, server="ollama")
        if isinstance(response, str):
            raise RuntimeError(f"Не удалось инициализировать сессию: {response}")
        main_assistant_message = response.get("message", {}).get("content", "")
        if not assistant_message:
            raise ValueError("Ollama вернула пустой ответ при инициализации сессии.")
        #обработка ошибки
    except json.JSONDecodeError:
        print(f"[First Step Warning] Не удалось распарсить JSON от модели: {assistant_message}")

    return assistant_message