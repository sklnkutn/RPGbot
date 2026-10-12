from nicegui import ui
from services.loaders import load_characters
from services.utils import handle_selection_toggle

def create_char_dialog(selected_characters: list):
    """Создает и возвращает диалоговое окно выбора персонажей"""
    characters = load_characters()

    with ui.dialog() as char_dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label("Выберите до 3 персонажей").classes("text-lg font-bold q-mb-md")
        
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

    return char_dialog