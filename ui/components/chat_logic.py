import asyncio
from nicegui import ui
from services.db import get_session_messages, save_message

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

async def handle_send(session_id: int, user_input, chat_container, chat_scroll):
    """Асинхронная обработка ввода и отправки сообщения"""
    text = user_input.value.strip()
    if not text or not session_id:
        ui.notify("Введите сообщение", type="negative", position="top")
        return
    
    # Сохранение, отображение сообщения пользователя
    await save_message(session_id, sender="user", text=text)
    user_input.value = ""
    await render_messages(session_id, chat_container, chat_scroll)
    chat_scroll.scroll_to(percent=1.0)
    
    # Заглушка ответ ИИ
    ai_response_text = f"Эхо от ИИ на ваше действие: «{text}». Мир вокруг начинает меняться..."
    ai_image_path = "assets/img/fr_del/example.jpg"
    
    # Сохранение, отображение сообщения ИИ
    await save_message(session_id, sender="assistant", text=ai_response_text, image_path=ai_image_path)
    await render_messages(session_id, chat_container, chat_scroll)
    chat_scroll.scroll_to(percent=1.0)