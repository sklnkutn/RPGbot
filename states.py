from aiogram.fsm.state import State, StatesGroup

class GameStates(StatesGroup):
    START = State()  # Начальное состояние
    IN_PROGRESS = State()  # Состояние, когда игра в процессе
    END = State()  # Конечное состояние