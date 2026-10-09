from nicegui import ui

#dialog = ui.dialog() #Объект диалога

#with dialog, ui.card().classes("w-full max-w-lg"): #Структура объекта диалога
#    ui.label("Выберите до 3 персонажей").classes("text-lg font-bold")
#    #карточки персонажей
#    ui.button("Закрыть", on_click=dialog.close)

def setup_routes(): #Регистрация декораторов модулей и тд
    """Регистрация всех страниц и маршрутов UI"""

    @ui.page("/") #формирование главной страницы
    async def main_page():

        #формирование опции диалогового окна внутри страницы для персонажей
        with ui.dialog() as char_dialog, ui.card().classes("w-full max-w-lg"):
            ui.label("Выберите до 3 персонажей").classes("text-lg font-bold q-mb-md")
            #Карточки персонажей
            ui.label("Слот для карточек персонажей").classes(
                "text-gray-400 q-mb-md"
            )
            ui.button("ЗАКРЫТЬ", on_click=char_dialog.close).props(
                "color=negative flat"
            )

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
        