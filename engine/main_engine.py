import os
from dotenv import load_dotenv
from services.db import save_message, get_session_info, get_active_session_characters, get_unsummarized_messages
from engine.first_assistant_ask import first_assistant_ask
from engine.second_assistant_ask import second_assistant_ask
from engine.third_assistant_ask import third_assistant_ask
from engine.fourth_assistant_ask import fourth_assistant_ask
from engine.fifth_assistant_ask import fifth_assistant_ask
from engine.comfy_ask import generate_comfy_image

load_dotenv()
MAX_MESSAGE_COUNT_BEFORE_SUMM = int(os.getenv("MAX_MESSAGE_COUNT_BEFORE_SUMM", 20))

async def process_player_turn(session_id: int, user_text: str) -> str:
    """
    Полный конвейер обработки хода игрока:
    1. Определение активного спутника (или активация через Шаг 1).
    2. Сохранение действия игрока с привязкой к спутнику.
    3. Генерация текста сцены Нарратором (Шаг 2).
    4. Создание визуального промпта (Шаг 3).
    5. Оценка психологического состояния и одежды (Шаг 4, если есть спутник).
    6. Генерация кадра через ComfyUI (после завершения работы LLM во избежание ООМ).
    7. Сохранение ответа истории в БД.
    8. Проверка буфера и архивация/суммаризация памяти (Шаг 5).
    """
    # 1. Получаем параметры сессии
    session_info = await get_session_info(session_id)
    adventure_id = session_info.get("adventure_id")
    llm_model = session_info.get("llm_model")
    comfy_model = session_info.get("comfy_model")

    try:
        # 2. Проверяем наличие активного персонажа на начало хода
        active_chars = await get_active_session_characters(session_id)
        
        if not active_chars:
            print("[Pipeline] Активных спутников нет на сцене. Запуск Шага 1 (Анализ входа)...")
            await first_assistant_ask(
                session_id=session_id,
                adventure_id=adventure_id,
                user_text=user_text,
                model_name=llm_model
            )
            # Перепроверяем: вдруг Шаг 1 только что активировал персонажа
            active_chars = await get_active_session_characters(session_id)
        else:
            print(f"[Pipeline] Спутник '{active_chars[0]}' уже на сцене. Шаг 1 пропущен.")

        active_char_id = active_chars[0] if active_chars else None

        # 3. Фиксируем действие игрока в БД, привязав его к текущему спутнику
        await save_message(
            session_id=session_id,
            sender="user",
            text=user_text,
            character_id=active_char_id
        )

        # 4. Шаг 2: Нарратор развивает события и реплики
        print("[Pipeline] Запуск Шага 2 (Генерация нарратива)...")
        narrator_text = await second_assistant_ask(
            session_id=session_id,
            adventure_id=adventure_id,
            active_char_id=active_char_id,
            model_name=llm_model
        )

        # 5. Шаг 3: Визуальный ассистент переводит сцену в промпт для диффузии
        print("[Pipeline] Запуск Шага 3 (Создание visual prompt)...")
        image_prompt = await third_assistant_ask(
            session_id=session_id,
            active_char_id=active_char_id,
            narrator_text=narrator_text,
            model_name=llm_model
        )

        # 6. Шаг 4: Оценка реакции спутника, сдвига отношений и одежды
        if active_char_id:
            print(f"[Pipeline] Запуск Шага 4 (Оценка состояния '{active_char_id}')...")
            await fourth_assistant_ask(
                session_id=session_id,
                active_char_id=active_char_id,
                narrator_text=narrator_text,
                image_prompt=image_prompt,
                model_name=llm_model
            )

        # 7. Генерация изображения через ComfyUI
        # Ollama закончила тяжелые фазы хода — безопасно отдаем VRAM под диффузию
        print("[Pipeline] Запуск ComfyUI (Рендер изображения сцены)...")
        image_path = await generate_comfy_image(
            session_id=session_id,
            comfy_model=comfy_model,
            positive_prompt=image_prompt
        )

        # 8. Сохраняем финальный ответ сцены в историю сообщений
        await save_message(
            session_id=session_id,
            sender="assistant",
            text=narrator_text,
            image_path=image_path,
            character_id=active_char_id
        )

        # 9. Шаг 5: Проверка лимита буфера и сжатие контекста
        unsummarized = await get_unsummarized_messages(session_id)
        if len(unsummarized) >= MAX_MESSAGE_COUNT_BEFORE_SUMM:
            print(f"[Pipeline] Буфер накопления полон ({len(unsummarized)} сообщений). Запуск Шага 5 (Суммаризация)...")
            await fifth_assistant_ask(session_id=session_id, model_name=llm_model)

        return narrator_text

    except Exception as e:
        error_msg = f"[Ошибка игрового конвейера]: {e}"
        print(error_msg)
        return error_msg