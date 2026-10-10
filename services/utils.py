from nicegui import ui

def handle_selection_toggle(item_id, checkbox, card, selected_list, max_limit, item_type_name="элементов"):
    """
    Универсальная логика выбора/отмены элементов (персонажей или истории)
    """
    if checkbox.value:
        if len(selected_list) >= max_limit:
            ui.notify(f"Можно выбрать не более {max_limit} {item_type_name}", type="warning")
            checkbox.value = False
        else:
            if item_id not in selected_list:
                # Если лимит == 1 (как для историй), можно автоматически очищать прошлый выбор
                if max_limit == 1:
                    selected_list.clear()
                selected_list.append(item_id)
                card.classes(add="bg-blue-50")
    else:
        if item_id in selected_list:
            selected_list.remove(item_id)
            card.classes(remove="bg-blue-50")
    
    print(f"Текущий выбор ({item_type_name}): {selected_list}")