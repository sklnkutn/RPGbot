import asyncio
from nicegui import ui
from services.db import create_session
from services.utils import validate_game_start
from ui.components.char_dialog import create_char_dialog
from ui.components.adv_dialog import create_adv_dialog
from ui.components.llm_settings import create_llm_settings
from ui.components.diff_model_settings import create_diff_model_settings
from ui.components.select_session import select_session
from engine.first_run import first_run

def setup_main_page():
    """Регистрация основной страницы"""
    @ui.page("/") #формирование главной страницы
    async def main_page():
        #Фиксация выбора
        selected_characters, selected_adventures = [], [] #Состояние выбранных персонажей(хранение ID), приключений
        # Инстанцируем компоненты диалогов
        char_dialog = create_char_dialog(selected_characters)
        adv_dialog = create_adv_dialog(selected_adventures)
        #Формирование контейнера по центру
        with ui.column().classes("w-full max-w-3xl mx-auto q-pa-lg items-center"):
            #Изображение лого
            ui.image('./static/logo.png').classes('w-1/3 max-w-[1024px] rounded-lg q-mb-md') 
            #Текст приветсвие
            ui.label(
                "Добро пожаловать в нашего бота.\n"
                "Готов погрузиться в мир RPG и приключений?\n"
                "Выбери желаемые настройки и начни свое путешеcтвие прямо сейчас!"
            ).classes("text-gray-400 text-center q-mb-lg")
            #Выбор моделей LLM, ComfyUI(выпадающие списки)
            with ui.card().classes("w-full q-pa-md q-mb-md bg-grey-9 text-white"):
                ui.label("Настройка генерации").classes("text-sm text-gray-400 font-bold q-mb-sm text-center w-full")
                # Один общий ряд для всех элементов в одну линию
                with ui.row().classes("w-full q-gutter-x-sm items-center"):
                    llm_select = create_llm_settings()
                    checkpoint_select = create_diff_model_settings()
            #Настройки сюжета
            ui.label("Настройки сюжета").classes("text-sm text-gray-500 q-mb-xs")
            with ui.row().classes("w-full q-gutter-x-sm q-mb-md"):
                ui.button(
                    "Выбор персонажей", icon="person_add", on_click=char_dialog.open
                    ).classes("col")
                ui.button(
                    "Выбор истории", icon="auto_stories", on_click=adv_dialog.open
                    ).classes("col")
            # Функция валидации и старта приключения с записью в бд
            is_starting = False
            async def start_adventure():
                nonlocal is_starting
                if is_starting:
                    return

                is_starting = True
                start_button.disable()
                try:
                    #Завершилась ли фоновая инициализация селектов
                    if not getattr(llm_select, 'is_ready', False) or not getattr(checkpoint_select, 'is_ready', False):
                        ui.notify("Подождите, идет загрузка списка моделей с серверов...", type="warning", position="top")
                        return

                    #Проверяем, что выбранные значения — это не тексты-заглушки ошибки/ожидания
                    invalid_states = ["Ожидание подключения к серверу...", "модели не обнаружены", "Сервер недоступен"]

                    if llm_select.value in invalid_states or checkpoint_select.value in invalid_states:
                        ui.notify("Невозможно начать историю: проверьте подключение к Ollama и ComfyUI", type="negative", position="top")
                        return

                    # 1. Проверяем через валидатор
                    error_message = validate_game_start(selected_adventures, selected_characters)
                    if error_message:
                        ui.notify(error_message, type="warning", position="top")
                        return

                    adventure_id=selected_adventures[0]
                    
                    session_id = await create_session(
                        adventure_id=adventure_id,
                        llm_model=llm_select.value,
                        comfy_model=checkpoint_select.value,
                        character_ids=selected_characters
                    )
                    await first_run(
                        session_id=session_id, 
                        adventure_id=adventure_id, 
                        model_name=llm_select.value
                    )
                    ui.notify(f"Сессия #{session_id} успешно создана!", type="positive", position="top")
                    ui.navigate.to(f'/adventure?session_id={session_id}')
                except Exception as e:
                    ui.notify(f"Ошибка создания сессии: {e}", type="negative", position="top")
                    print(f"DB Error: {e}")
                finally:
                    is_starting = False
                    start_button.enable()

            #Главная кнопка старта
            start_button = ui.button("НАЧАТЬ ИСТОРИЮ", icon="play_arrow", on_click=start_adventure).props(
                "color=green size=lg"
            ).classes("w-full font-bold")
            open_session_dialog = select_session()
            ui.button("ЗАГРУЗИТЬ ИСТОРИЮ", icon="history", on_click=open_session_dialog).props(
                "color=green size=lg"
            ).classes("w-full font-bold")