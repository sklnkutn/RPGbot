import os
from dotenv import load_dotenv
from services.states import GameStates
from services.logger import logger, state_logger
from services.db import commit_player_turn, get_session_info, get_active_session_characters, get_unsummarized_messages
from engine.first_assistant_ask import first_assistant_ask
from engine.second_assistant_ask import second_assistant_ask
from engine.third_assistant_ask import third_assistant_ask
from engine.fourth_assistant_ask import fourth_assistant_ask
from engine.fifth_assistant_ask import fifth_assistant_ask
from engine.comfy_ask import generate_comfy_image
from engine.comfy_ask import delete_generated_image

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
    # Префикс для всех логов текущей функции
    ctx = f"[Session #{session_id}]"
    logger.info(f"{ctx} === Старт обработки хода игрока ===")

    # 1. Получаем параметры сессии
    session_info = await get_session_info(session_id)
    if not session_info:
        logger.info(f"{ctx} Сессия #{session_id} не найдена)...")
        raise ValueError(f"Сессия #{session_id} не найдена")

    if session_info["state"] != GameStates.IN_PROGRESS.value:
        logger.info(f"{ctx} Сессия #{session_id} не активна)...")
        raise ValueError(f"Сессия #{session_id} не активна")

    adventure_id = session_info.get("adventure_id")
    llm_model = session_info.get("llm_model")
    comfy_model = session_info.get("comfy_model")

    try:
        # 2. Проверяем наличие активного персонажа на начало хода
        active_chars = await get_active_session_characters(session_id)
        
        if not active_chars:
            logger.info(f"{ctx} [Шаг 1] Активных спутников нет. Запуск анализа входа...")
            active_char_id = await first_assistant_ask(
                session_id=session_id,
                adventure_id=adventure_id,
                user_text=user_text,
                model_name=llm_model
            )
        else:
            logger.info(f"{ctx} [Шаг 1] Спутник '{active_chars[0]}' на сцене. Пропуск активации.")
            active_char_id = active_chars[0]

        # 4. Шаг 2: Нарратор развивает события и реплики
        logger.info(f"{ctx} [Шаг 2] Генерация нарратива...")
        narrator_text = await second_assistant_ask(
            session_id=session_id,
            adventure_id=adventure_id,
            active_char_id=active_char_id,
            model_name=llm_model,
            user_text=user_text,
        )

        # 5. Шаг 3: Визуальный ассистент переводит сцену в промпт для диффузии
        logger.info(f"{ctx} [Шаг 3] Создание визуального промпта...")
        image_prompt = await third_assistant_ask(
            session_id=session_id,
            active_char_id=active_char_id,
            narrator_text=narrator_text,
            model_name=llm_model
        )

        # 6. Шаг 4: Оценка реакции спутника, сдвига отношений и одежды
        character_state = None
        if active_char_id:
            logger.info(f"{ctx} [Шаг 4] Оценка состояния персонажа '{active_char_id}'...")
            character_state = await fourth_assistant_ask(
                session_id=session_id,
                active_char_id=active_char_id,
                narrator_text=narrator_text,
                image_prompt=image_prompt,
                model_name=llm_model
            )

        # 7. Генерация изображения через ComfyUI
        # Ollama закончила тяжелые фазы хода — безопасно отдаем VRAM под диффузию
        logger.info(f"{ctx} [ComfyUI] Отправка в очередь рендера (модель: {comfy_model})...")
        image_path = await generate_comfy_image(
            session_id=session_id,
            comfy_model=comfy_model,
            positive_prompt=image_prompt
        )
        if not image_path:
            raise RuntimeError("ComfyUI не смог сгенерировать или сохранить изображение. Ход не записан.")

        try:
            await commit_player_turn(
                session_id=session_id,
                user_text=user_text,
                narrator_text=narrator_text,
                image_path=image_path,
                character_id=active_char_id,
                character_state=character_state,
            )
        except BaseException:
            try:
                await delete_generated_image(image_path)
            except Exception:
                logger.exception(f"{ctx} Не удалось удалить изображение незаписанного хода")
            raise

        # Архивация выполняется после фиксации хода и не меняет его статус для пользователя.
        try:
            unsummarized = await get_unsummarized_messages(session_id)
            if len(unsummarized) >= MAX_MESSAGE_COUNT_BEFORE_SUMM:
                logger.info(f"{ctx} [Шаг 5] Накоплено {len(unsummarized)} сообщений. Запуск суммаризации...")
                await fifth_assistant_ask(session_id=session_id, model_name=llm_model)
        except Exception:
            logger.exception(f"{ctx} Ошибка суммаризации после успешного сохранения хода")

        return narrator_text

    except Exception as e:
        error_msg = f"[Ошибка игрового конвейера]: {e}"
        logger.error(f"{ctx} Ошибка в игровом конвейере: {e}", exc_info=True)
        raise RuntimeError(error_msg) from e