from nicegui import ui

from services.db import get_all_active_sessions, get_session_characters_list
from services.loaders import load_adventures, load_characters
from services.logger import logger


def select_session():
    """Создает диалог выбора активной сессии для продолжения."""
    with ui.dialog() as session_dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label("Выберите историю для продолжения").classes("text-lg font-bold q-mb-md")
        with ui.scroll_area().classes("w-full h-96 q-mb-md"):
            sessions_container = ui.column().classes("w-full q-gutter-md")
        ui.button("ЗАКРЫТЬ", on_click=session_dialog.close).props("flat").classes("w-full")

    async def open_session_dialog():
        sessions_container.clear()
        try:
            sessions = await get_all_active_sessions()
            adventures = {adventure.get("id"): adventure for adventure in load_adventures()}
            characters = {character.get("id"): character for character in load_characters()}

            with sessions_container:
                if not sessions:
                    ui.label("Нет активных историй для загрузки.").classes(
                        "w-full text-center text-grey-7 q-pa-lg"
                    )

                for session in sessions:
                    session_id = session["id"]
                    adventure = adventures.get(session["adventure_id"], {})
                    adventure_name = adventure.get("name", session["adventure_id"])
                    adventure_image = adventure.get(
                        "resolved_image_path", "/assets/img/adv/in_prog.png"
                    )
                    character_ids = await get_session_characters_list(session_id)
                    character_names = [
                        characters.get(character_id, {}).get("name", character_id)
                        for character_id in character_ids
                    ]

                    with ui.card().classes("w-full q-pa-sm"):
                        with ui.row().classes("w-full items-center no-wrap"):
                            ui.image(adventure_image).classes(
                                "w-24 h-24 object-cover rounded-md"
                            )
                            with ui.column().classes("col"):
                                ui.label(adventure_name).classes("text-bold")
                                ui.label(f"Сессия #{session_id}").classes("text-xs text-grey-6")
                                ui.label(f"Создана: {session['created_at']}").classes(
                                    "text-xs text-grey-6"
                                )
                                ui.label(
                                    "Персонажи: " + (", ".join(character_names) or "не выбраны")
                                ).classes("text-sm")
                                ui.label(
                                    f"Модель: {session['llm_model']} · "
                                    f"ComfyUI: {session['comfy_model']}"
                                ).classes("text-xs text-grey-6")

                            ui.button(
                                "ПРОДОЛЖИТЬ",
                                on_click=lambda current_id=session_id: resume_session(current_id),
                            ).props("color=primary")
        except Exception:
            logger.exception("Не удалось загрузить список активных сессий")
            sessions_container.clear()
            with sessions_container:
                ui.label("Не удалось загрузить истории. Попробуйте еще раз.").classes(
                    "w-full text-center text-negative q-pa-lg"
                )
            ui.notify("Ошибка загрузки историй.", type="negative", position="top")

        session_dialog.open()

    return open_session_dialog


def resume_session(session_id: int) -> None:
    ui.navigate.to(f"/adventure?session_id={session_id}")
