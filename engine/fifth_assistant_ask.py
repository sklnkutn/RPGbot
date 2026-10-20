import os
import json
from dotenv import load_dotenv
from services.logger import logger
from services.loaders import load_character_data, load_prompt
from services.server_request import get_server_url, send_http_post
from services.db import get_chunk_for_summarization, mark_messages_as_summarized, save_session_summary_chunk, append_character_memories

load_dotenv()
MIN_MESSAGE_COUNT = int(os.getenv("MIN_MESSAGE_COUNT", 10))
MAX_MESSAGE_COUNT_BEFORE_SUMM = int(os.getenv("MAX_MESSAGE_COUNT_BEFORE_SUMM", 20))

async def fifth_assistant_ask(session_id: int, model_name: str):
    """
    Пятый шаг: сжатие старого буфера сообщений, извлечение долговременной памяти
    персонажей и запись архивного фрагмента сюжета.
    """
    #ID логгирования
    ctx = f"[Session #{session_id}] [Fifth Step]"
    logger.info(f"{ctx} Запуск сжатия буфера и извлечения памяти...")

    # Размер сжимаемого чанка — это дельта между максимумом и минимумом
    chunk_size = MAX_MESSAGE_COUNT_BEFORE_SUMM - MIN_MESSAGE_COUNT
    if chunk_size <= 0:
        chunk_size = 10

    # 1. Забираем старые сообщения для архивации
    chunk_messages = await get_chunk_for_summarization(session_id, chunk_size=chunk_size)
    if not chunk_messages:
        return
    logger.debug(f"{ctx} Размер сжимаемого буфера: {len(chunk_messages)} сообщений.")

    # Собираем сырой текст диалога для передачи модели
    formatted_dialogue = "\n".join([
        f"{'Игрок' if m['sender'] == 'user' else 'Нарратор'}: {m['text']}"
        for m in chunk_messages
    ])

    # 2. Определяем, какие персонажи реально участвовали в этом чанке
    participating_char_ids = list({
        m["character_id"] for m in chunk_messages if m.get("character_id")
    })

    # 3. ФАЗА А: Извлечение фактов для каждого персонажа отдельно (изолированно)
    if participating_char_ids:
        fact_prompt_template = load_prompt("fact_extractor_prompt.yaml")
        fact_schema = {
            "about_player": {"type": "array", "items": {"type": "string"}},
            "about_world": {"type": "array", "items": {"type": "string"}},
            "about_self": {"type": "array", "items": {"type": "string"}}
        }

        for char_id in participating_char_ids:
            char_yaml = load_character_data(char_id)
            char_context = (
                f"# Персонаж, анализирующий диалог: {char_yaml.get('name')}\n"
                f"- Черты: {', '.join(char_yaml.get('bio', {}).get('personality_traits', []))}\n"
            )

            fact_messages = [
                {"role": "system", "content": f"{fact_prompt_template}\n\n{char_context}"},
                {"role": "user", "content": f"[ОТРЕЗОК ДИАЛОГА ДЛЯ АНАЛИЗА ПАМЯТИ]:\n{formatted_dialogue}"}
            ]

            payload = {
                "model": model_name,
                "messages": fact_messages,
                "format": {
                    "type": "object",
                    "properties": fact_schema,
                    "required": ["about_player", "about_world", "about_self"]
                },
                "stream": False,
                "keep_alive": 0,
                "options": {"temperature": 0.2, "num_ctx": 3072}
            }

            url = get_server_url("ollama", "api/chat")
            res = await send_http_post(url, payload, server="ollama")
            if not isinstance(res, str):
                try:
                    facts = json.loads(res.get("message", {}).get("content", "{}"))
                    logger.info(f"{ctx} Персонаж '{char_id}' обновил память: извлечено фактов (player: {len(facts.get('about_player', []))}, world: {len(facts.get('about_world', []))})")
                    # Сохраняем новые факты в память персонажа
                    await append_character_memories(session_id, char_id, facts)
                except Exception as e:
                    logger.error(f"{ctx} Ошибка парсинга или сохранения фактов для {char_id}: {e}", exc_info=True)

    # 4. ФАЗА Б: Литературная суммаризация событий чанка в общую хронику (session_summaries)
    summary_prompt_template = load_prompt("chunk_summary_prompt.yaml")

    summary_messages = [
        {"role": "system", "content": summary_prompt_template},
        {"role": "user", "content": f"[СОБЫТИЯ ДЛЯ СЖАТИЯ]:\n{formatted_dialogue}"}
    ]

    summary_payload = {
        "model": model_name,
        "messages": summary_messages,
        "stream": False,
        "keep_alive": 0,
        "options": {"temperature": 0.5, "num_ctx": 3072}
    }

    url = get_server_url("ollama", "api/chat")
    sum_res = await send_http_post(url, summary_payload, server="ollama")
    
    if isinstance(sum_res, str):
        logger.error(f"{ctx} Ошибка сети при суммаризации: {sum_res}")
        return
    
    summary_text = sum_res.get("message", {}).get("content", "").strip()

    if not summary_text:
        logger.warning(f"{ctx} Модель вернула пустое резюме. Пропускаем сохранение.")
        return
        
    # 5. Записываем архивный чанк в базу данных
    start_id = chunk_messages[0]["id"]
    end_id = chunk_messages[-1]["id"]
    await save_session_summary_chunk(session_id, start_id, end_id, summary_text)

    logger.info(f"{ctx} Успешно создано и сохранено архивное резюме для сообщений ID {start_id}-{end_id}.")

    # 6. Помечаем эти сообщения как сжатые (is_summarized = 1)
    message_ids = [m["id"] for m in chunk_messages]
    await mark_messages_as_summarized(message_ids)

    logger.debug(f"{ctx} Помечено как сжатое сообщений: {len(message_ids)}")