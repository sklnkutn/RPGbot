from nicegui import ui

def create_diff_model_settings():
    """Создает селект для визуализации и иконку."""
    checkpoint_select = (
        ui.select(
            options=["WAI.safetensors", "nova_furry.safetensors", "illustmix.safetensors"],
            value="WAI.safetensors",
            label="Модель визуализации"
        )
        .classes("col")
        .props("outlined dense dark")
    )
    ui.icon("image", size="sm").classes("text-gray-400")
    return checkpoint_select