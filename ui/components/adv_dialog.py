from nicegui import ui
from services.loaders import load_adventures
from services.utils import handle_selection_toggle

def create_adv_dialog(selected_adventures: list):
    """Создает и возвращает диалоговое окно выбора истории"""
    adventures = load_adventures()

    with ui.dialog() as adv_dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label("Выберите сюжет истории").classes("text-lg font-bold q-mb-md")
        
        with ui.scroll_area().classes("w-full h-96 q-mb-md"):
            with ui.row().classes("w-full wrap q-col-gutter-md justify-center"):
                for adv in adventures:
                    adv_id = adv.get("id")
                    name = adv.get("name")
                    description = adv.get("description")
                    img_path = adv["resolved_image_path"]

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

    return adv_dialog