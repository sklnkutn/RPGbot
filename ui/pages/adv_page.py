import asyncio
from nicegui import ui
from services.db import get_session_info
from services.logger import logger
from services.states import GameStates
from ui.components.chat_logic import render_messages, handle_send
from ui.components.show_session_error import show_session_error

def setup_adv_page():
    """Регистрация страницы приключений"""
    @ui.page("/adventure")
    async def adventure_page(session_id: int | None = None):
        if session_id is None:
            show_session_error(
                "Не указан номер сессии.",
                "Вернитесь на главную страницу и начните новую историю.",
            )
            return

        try:
            session_info = await get_session_info(session_id)
        except Exception:
            logger.exception(f"Не удалось проверить сессию #{session_id}")
            show_session_error(
                "Не удалось проверить состояние сессии.",
                "Попробуйте перезагрузить страницу. Если ошибка повторится, обратитесь к администратору.",
            )
            return

        if not session_info:
            show_session_error(
                f"Сессия #{session_id} не найдена.",
                "Возможно, ссылка устарела или сессия была удалена.",
            )
            return

        if session_info["state"] != GameStates.IN_PROGRESS.value:
            if session_info["state"] == GameStates.ON_HOLD.value:
                message = "Эта сессия приостановлена."
                details = "Продолжение сессии пока недоступно."
            elif session_info["state"] == GameStates.END.value:
                message = "Эта сессия завершена."
                details = "Начните новую историю, чтобы продолжить игру."
            else:
                message = "Сессия находится в неизвестном состоянии."
                details = "Продолжение игры заблокировано до проверки состояния сессии."

            show_session_error(message, details)
            return

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
        
        #Нижнее окно ввода и отправки
        with ui.footer().classes("bg-grey-9 q-pa-md items-center"):
            #ui.button(icon="menu", on_click=left_drawer.toggle).props("flat round dense size=md text-color=grey")
            with ui.row().classes("w-full max-w-4xl mx-auto items-center q-gutter-x-sm"):
                ui.button(icon="menu", on_click=left_drawer.toggle).props("flat round dense size=md text-color=grey")
                user_input = ui.textarea(placeholder="Введите ваше действие или реплику...").props("outlined dense rows=3 dark").classes("flex-grow bg-grey-8")
                #кнопка отправить обновить           
                with ui.column().classes("w-1/5"):
                    send_button = ui.button(icon="send", on_click=lambda: handle_send(session_id, user_input, chat_container, chat_scroll, send_button)).props("color=primary unelevated").classes("h-4")
                    ui.button(icon="refresh", on_click=lambda: ui.notify("Перегенерация (заглушка)")).props("color=grey flat text-color=white").classes("h-4")

        #первоначальный рендер при открытии
        ui.timer(0.1, lambda: render_messages(session_id, chat_container, chat_scroll), once=True)