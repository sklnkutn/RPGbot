from nicegui import ui

def show_session_error(message: str, details: str) -> None:
    with ui.column().classes("w-full h-screen items-center justify-center"):
        with ui.card().classes("w-full max-w-xl q-pa-lg"):
            ui.label("Не удалось открыть приключение").classes("text-h5")
            ui.label(message).classes("text-negative q-mt-md")
            ui.label(details).classes("q-mt-sm")
            ui.button(
                "На главную",
                on_click=lambda: ui.navigate.to("/"),
            ).props("color=primary").classes("q-mt-md")