import asyncio
from nicegui import ui
from services.loaders import load_characters, load_adventures
from services.utils import handle_selection_toggle
from services.db import create_session, get_session_messages, save_message

def setup_routes(): #Регистрация декораторов модулей и тд
    """Регистрация всех страниц и маршрутов UI"""

    @ui.page("/") #формирование главной страницы
    async def main_page():

        #Фиксация выбора
        selected_characters = [] #Состояние выбранных персонажей(хранение ID)
        selected_adventures = [] #Состояние выбранного персонажа
        
        #Загрузка переменных
        characters = load_characters () #Загрузка персонажей из YAML при открытии страницы
        adventures = load_adventures () #Загрузка приключений из YAML при открытии страницы

        #формирование опции диалогового окна внутри страницы для персонажей
        with ui.dialog() as char_dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label("Выберите до 3 персонажей").classes("text-lg font-bold q-mb-md")
            
            #Контейнер для карточек с прокруткой
            with ui.scroll_area().classes("w-full h-96 q-mb-md"):
                with ui.row().classes("w-full wrap q-col-gutter-md justify-center"):
                    for char in characters:
                        char_id = char.get("id")
                        name = char.get("name")
                        alias = char.get("alias")
                        img_path = char["visual"]["resolved_image_path"]
                        bio_data = char.get("bio", {})
                        description = bio_data.get("description", "нет описания")
                        age = bio_data.get("age", "")

                        #Карточка одного персонажа
                        with ui.card().classes("w-56 q-pa-sm items-center cursor-pointer") as card:
                            ui.image(img_path).classes("w-full h-52 object-cover rounded-md")
                            ui.label(name).classes("text-bold text-sm q-mt-xs text-center")
                            if alias is not None:
                                ui.label(f"{alias} ").classes("text-italic text-xs text-grey-6 text-center")
                            if age is not None:
                                ui.label(f"Возраст: {age}").classes("text-xs text-grey-7 text-center q-mt-xs")
                            if description is not None:
                                with ui.expansion("Биография", icon="menu_book").classes("w-full text-xs text-grey-8 q-mt-xs"):
                                    ui.label(description).classes("text-xs text-grey-7 q-pa-xs")

                            checkbox = ui.checkbox("Выбрать").classes("q-mt-xs")

                            checkbox.on_value_change(
                                lambda e, c_id=char_id, cb=checkbox, c_card=card: 
                                handle_selection_toggle(c_id, cb, c_card, selected_characters, max_limit=3, item_type_name="персонажей")
                            )

            ui.button("ГОТОВО", on_click=char_dialog.close).props("color=primary").classes("w-full")

        #формирование опции диалогового окна внутри страницы для историй
        with ui.dialog() as adv_dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label("Выберите сюжет истории").classes("text-lg font-bold q-mb-md")
            
            #Контейнер для карточек историй 
            with ui.scroll_area().classes("w-full h-96 q-mb-md"):
                with ui.row().classes("w-full wrap q-col-gutter-md justify-center"):
                    for adv in adventures:
                        adv_id = adv.get("id")
                        name = adv.get("name")
                        description = adv.get("description")
                        img_path = adv["resolved_image_path"]

                        #Карточка одного приключения
                        with ui.card().classes("w-56 q-pa-sm items-center cursor-pointer") as card:
                            ui.image(img_path).classes("w-full h-52 object-cover rounded-md")
                            ui.label(name).classes("text-bold text-sm q-mt-xs text-center")
                            ui.label(description).classes("text-xs text-grey-7 q-pa-xs")

                            checkbox = ui.checkbox("Выбрать").classes("q-mt-xs")

                            checkbox.on_value_change(
                                lambda e, a_id=adv_id, cb=checkbox, c_card=card: 
                                handle_selection_toggle(a_id, cb, c_card, selected_adventures, max_limit=1, item_type_name="приключение")
                            )
            ui.button("ГОТОВО", on_click=adv_dialog.close).props("color=primary").classes("w-full")                

        #Формирование контейнера по центру
        with ui.column().classes("w-full max-w-3xl mx-auto q-pa-lg items-center"):

            #Изображение лого
            ui.image('static/logo.png').classes('w-1/3 max-w-[1024px] rounded-lg q-mb-md') 
            
            #Текст приветсвие
            ui.label(
                "Добро пожаловать в нашего бота.\n"
                "Готов погрузиться в мир RPG и приключений?\n"
                "Выбери желаемые настройки и начни свое путешеcтвие прямо сейчас!"
            ).classes("text-gray-400 text-center q-mb-lg")

            #Выбор моделей LLM, ComfyUI(выпадающие списки)
            ui.label("Настройка генерации").classes("text-sm text-gray-500 q-mb-xs")
            with ui.row().classes("w-full q-gutter-x-sm q-mb-md"):
                ui.icon("psychology", size="sm").classes("text-gray-400")
                llm_select = (
                    ui.select(
                        options=["llama3:8b", "mistral:7b", "gemma2:9b"],
                        value="llama3:8b",
                        label="Модель LLM"
                    )
                    .classes("col")
                    .props("outlined dense")
                )
                
                checkpoint_select = (
                    ui.select(
                        options=["WAI.safetensors", "nova_furry.safetensors", "illustmix.safetensors"],
                        value="WAI.safetensors",
                        label="Модель визуализации"
                    )
                    .classes("col")
                    .props("outlined dense")
                )
                ui.icon("image", size="sm").classes("text-gray-400")
            
            #Настройки промпта генерации выпадающие списки
            ui.label("Настройки сюжета").classes("text-sm text-gray-500 q-mb-xs")
            with ui.row().classes("w-full q-gutter-x-sm q-mb-md"):
                ui.button(
                    "Выбор персонажей", icon="person_add", on_click=char_dialog.open
                    ).classes("col")
                ui.button(
                    "Выбор истории", icon="auto_stories", on_click=adv_dialog.open
                    ).classes("col")
            
            # Функция валидации и старта приключения с записью в бд
            async def start_adventure():
                if not selected_adventures:
                    ui.notify("Пожалуйста, выберите сюжет истории", type="warning", position="top")
                    return
                if not selected_characters:
                    ui.notify("Пожалуйста, выберите как минимум одного персонажа(до 3ех)", type="warning", position="top")
                    return
                
                adventure_id = selected_adventures[0]
                chosen_llm = llm_select.value
                chosen_comfy = checkpoint_select.value

                try:
                    # 3. Создаем сессию в базе данных и получаем ее ID
                    session_id = await create_session(
                        adventure_id=adventure_id,
                        llm_model=chosen_llm,
                        comfy_model=chosen_comfy,
                        character_ids=selected_characters
                    )
                    
                    ui.notify(f"Сессия #{session_id} успешно создана!", type="positive", position="top")
                    ui.navigate.to(f'/adventure?session_id={session_id}')

                except Exception as e:
                    ui.notify(f"Ошибка создания сессии: {e}", type="negative", position="top")
                    print(f"DB Error: {e}")

            #Главная кнопка старта
            ui.button("НАЧАТЬ ИСТОРИЮ", icon="play_arrow", on_click=start_adventure).props(
                "color=green size=lg"
            ).classes("w-full font-bold")
    
#Страница ведения истории
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