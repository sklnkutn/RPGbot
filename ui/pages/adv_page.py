import asyncio
from nicegui import ui
from services.db import get_session_messages, save_message

def setup_adv_page():
    """Регистрация страницы приключений"""
    @ui.page("/adventure")
    def adventure_page(session_id: int = None): #NiceGUI автоматически парсит Query-параметры из URL
        
        # Боковая панель левая (drawer)
        with ui.left_drawer(value=True).props("behavior=desktop").classes("bg-grey-9 p-4 flex flex-col justify-between h-full") as left_drawer:
            
            # Верхняя часть меню (всё, что должно быть сверху)
            with ui.column().classes("w-full items-center"):
                ui.label("МЕНЮ ПРИКЛЮЧЕНИЯ").classes("text-lg font-bold mb-4 text-center w-full")
                ui.button("НАЗАД НА ГЛАВНУЮ", on_click=lambda: ui.navigate.to('/')).props("color=grey").classes("mt-4")

            # Нижняя часть (идентификатор сессии уедет в самый низ)
            if session_id:
                ui.label(f"session_id: {session_id}").classes("text-[10px] text-gray-400 font-mono text-center w-full")
            else:
                ui.label("session: none").classes("text-[10px] text-red-400 font-mono text-center w-full")
    
        # Основное тело страницы
        with ui.column().classes("w-full mx-auto h-[calc(100vh-155px)] justify-between"):
            # Контейнер прокрутки для истории сообщений
            chat_scroll = ui.scroll_area().classes("w-full flex-grow")
            with chat_scroll:
                # Контейнер для самих сообщений
                chat_container = ui.column().classes("w-full")
        
        #Функция отрисовки сообщений
        async def render_messages():
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

        #Нижнее окно ввода и отправки
        with ui.footer().classes("bg-grey-9 q-pa-md items-center"):
            #ui.button(icon="menu", on_click=left_drawer.toggle).props("flat round dense size=md text-color=grey")
            with ui.row().classes("w-full max-w-4xl mx-auto items-center q-gutter-x-sm"):
                ui.button(icon="menu", on_click=left_drawer.toggle).props("flat round dense size=md text-color=grey")
                user_input = ui.textarea(placeholder="Введите ваше действие или реплику...").props("outlined dense rows=3 dark").classes("flex-grow bg-grey-8")
                #Асинхронная обработка ввода
                async def handle_send():
                    text = user_input.value.strip()
                    if not text or not session_id:
                        ui.notify("Введите сообщение", type="negative", position="top")
                        return
                    #сохранение, отображение сообщения пользователя
                    await save_message(session_id, sender="user", text=text)
                    user_input.value = ""
                    await render_messages()
                    chat_scroll.scroll_to(percent=1.0)
                    #Заглушка ответ ии
                    ai_response_text = f"Эхо от ИИ на ваше действие: «{text}». Мир вокруг начинает меняться..."
                    ai_image_path = "assets/img/fr_del/example.jpg"
                    #Сохранение, отображение сообщения ИИ
                    await save_message(session_id, sender="assistant", text=ai_response_text, image_path=ai_image_path)
                    await render_messages()
                    chat_scroll.scroll_to(percent=1.0)
                #кнопка отправить обновить           
                with ui.column().classes("w-1/5"):
                    ui.button(icon="send", on_click=handle_send).props("color=primary unelevated").classes("h-4")
                    ui.button(icon="refresh", on_click=lambda: ui.notify("Перегенерация (заглушка)")).props("color=grey flat text-color=white").classes("h-4")

        #первоначальный рендер при открытии
        ui.timer(0.1, render_messages, once=True)