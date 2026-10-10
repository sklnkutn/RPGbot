from nicegui import ui
from services.loader import load_characters

def setup_routes(): #Регистрация декораторов модулей и тд
    """Регистрация всех страниц и маршрутов UI"""

    @ui.page("/") #формирование главной страницы
    async def main_page():

        selected_characters = [] #Состояние выбранных персонажей(хранение ID)

        characters = load_characters () #Загрузка персонажей из YAML при открытии страницы

        #формирование опции диалогового окна внутри страницы для персонажей
        with ui.dialog() as char_dialog, ui.card().classes("w-full max-w-lg"):
            ui.label("Выберите до 3 персонажей").classes("text-lg font-bold q-mb-md")
            
            #Контейнер для карточек с прокруткой
            with ui.scroll_area().classes("w-full h-72 q-mb-md"):
                with ui.row().classes("w-full q-col-gutter-sm justify-center"):
                    for char in characters:
                        char_id = char.get("id")
                        name = char.get("name")
                        alias = char.get("alias")
                        img_path = char["visual"]["resolved_image_path"]
                        bio_data = char.get("bio", {})
                        description = bio_data.get("description", "нет описания")
                        age = bio_data.get("age", "")

                        #Карточка одного персонажа
                        with ui.card().classes("w-60 q-pa-sm items-center cursor-pointer") as card:
                            ui.image(img_path).classes("w-full h-32 object-cover rounded-md")
                            ui.label(name).classes("text-bold text-sm q-mt-xs text-center")
                            ui.label(f"{alias} ").classes("text-italic text-xs text-grey-6 text-center")
                            ui.label(f"Возраст: {age}").classes("text-xs text-grey-7 text-center q-mt-xs")
                            ui.label(description).classes("text-xs text-grey-7 text-center q-mt-xs ellipsis-3-lines")

                            checkbox = ui.checkbox("Выбрать").classes("q-mt-xs")

                            #Логика выбора до 3
                            def toggle_selection(c_id=char_id, cb=checkbox, c_card=card):
                                if cb.value:
                                    if len(selected_characters) >= 3:
                                        ui.notify("Можно выбрать не более 3 персонажей", type="warning")
                                        cb.value = False
                                    else:
                                        if c_id not in selected_characters:
                                            selected_characters.append(c_id)
                                            c_card.classes(add="bg-blue-50") #подсветка
                                else:
                                    if c_id in selected_characters:
                                        selected_characters.remove(c_id)
                                        c_card.classes(remove="bg-blue-50")
                                print(f"Текущий выбор персонажей: {selected_characters}")
                            
                            checkbox.on_value_change(toggle_selection)
            ui.button("ГОТОВО", on_click=char_dialog.close).props("color=primary").classes("w-full")
            #ui.label("Слот для карточек персонажей").classes(
            #    "text-gray-400 q-mb-md"
            #)
            #ui.button("ЗАКРЫТЬ", on_click=char_dialog.close).props(
            #    "color=negative flat"
            #)

        #формирование опции диалогового окна внутри страницы для историй
        with ui.dialog() as stories_dialog, ui.card().classes("w-full max-w-lg"):
            ui.label("Выберите сюжет истории").classes("text-lg font-bold q-mb-md")
            #Карточки историй
            ui.label("Слот для карточек историй").classes(
                "text-gray-400 q-mb-md"
            )
            ui.button("ЗАКРЫТЬ", on_click=stories_dialog.close).props(
                "color=negative flat"
            )

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
                    "Выбор истории", icon="auto_stories", on_click=stories_dialog.open
                    ).classes("col")
            
            #Главная кнопка старта
            ui.button("НАЧАТЬ ИСТОРИЮ", icon="play_arrow").props(
                "color=green size=lg"
            ).classes("w-full font-bold")
        