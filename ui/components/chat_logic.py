import asyncio
from nicegui import ui
from services.db import get_session_messages
from engine.main_engine import process_player_turn

# Словарь для хранения блокировок по каждой сессии
session_locks = {}

async def render_messages(session_id: int, chat_container, chat_scroll):
    """Функция отрисовки сообщений"""
    chat_container.clear()
    messages = await get_session_messages(session_id)
    
    for msg in messages:
        sender = msg["sender"]
        text = msg["text"]
        image_path = msg["image_path"]
                
        with chat_container:
            if sender == "user":
                with ui.row().classes("w-full justify-end"):
                    with ui.card().classes("bg-blue-100 max-w-xl"):
                        ui.label(text).classes("text-sm")
            else:
                with ui.card().classes("bg-white max-w-xl"):
                    if image_path:
                        ui.image(image_path).classes("w-full h-auto object-contain rounded-md")
                    ui.label(text).classes("text-sm text-grey-9")
    await asyncio.sleep(0.05)
    chat_scroll.scroll_to(percent=1.1)

async def handle_send(session_id: int, user_input, chat_container, chat_scroll, send_button = None):
    """Асинхронная обработка ввода и отправки сообщения"""
    text = user_input.value.strip()
    if not text or not session_id:
        ui.notify("Введите сообщение", type="negative", position="top")
        return
    # Инициализируем лок для сессии, если его еще нет
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    # Проверяем, занята ли сессия обработкой предыдущего хода
    if session_locks[session_id].locked():
        ui.notify("Подождите, предыдущий ход еще обрабатывается...", type="warning", position="top")
        return    
    user_input.disable()
    if send_button:
        send_button.disable()
        send_button.props('loading')

    async with session_locks[session_id]:

        try:
            ui.notify("Анализ хода...", type="info", position="top", timeout=1000)

            async def on_turn_committed():
                user_input.value = ""
                try:
                    await render_messages(session_id, chat_container, chat_scroll)
                except Exception as e:
                    ui.notify(
                        f"Ход сохранён, но не удалось обновить историю: {e}. Перезагрузите страницу.",
                        type="warning",
                        position="top",
                    )
                finally:
                    user_input.enable()

            # Запускаем наш конвейер обработки хода
            await process_player_turn(
                session_id=session_id,
                user_text=text,
                on_turn_committed=on_turn_committed,
            )

        except Exception as e:
            ui.notify(f"Ошибка: {e}", type="negative", position="top")
            print(f"Chat Logic Error: {e}")
        finally:
            # Всегда разблокируем интерфейс в блоке finally
            user_input.enable()
            if send_button:
                send_button.enable()
                send_button.props(remove='loading')        