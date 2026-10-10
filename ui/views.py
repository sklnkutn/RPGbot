from nicegui import ui
from services.loaders import load_characters, load_adventures
from services.utils import handle_selection_toggle

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
                #ui.button("Модель LLM", icon="psychology").classes("col") 
                
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
                #ui.button("Модель визуализации", icon="image").classes("col")
            
            #Настройки промпта генерации выпадающие списки
            ui.label("Настройки сюжета").classes("text-sm text-gray-500 q-mb-xs")
            with ui.row().classes("w-full q-gutter-x-sm q-mb-md"):
                ui.button(
                    "Выбор персонажей", icon="person_add", on_click=char_dialog.open
                    ).classes("col")
                ui.button(
                    "Выбор истории", icon="auto_stories", on_click=adv_dialog.open
                    ).classes("col")
            
            #Главная кнопка старта
            ui.button("НАЧАТЬ ИСТОРИЮ", icon="play_arrow").props(
                "color=green size=lg"
            ).classes("w-full font-bold")
        