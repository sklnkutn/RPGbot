from enum import Enum

class GameStates(str, Enum):
    """Состояние игровой сессии"""
    IN_PROGRESS = "in_progress"  # Активная стадия сессии
    ON_HOLD = "on_hold"  # Сессия на паузе / приостановленна
    END = "end"  # сессия завершена