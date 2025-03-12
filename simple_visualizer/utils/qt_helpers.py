from contextlib import contextmanager
from typing import Sequence
from PySide6.QtCore import QObject

@contextmanager
def block_signals(*widgets: Sequence[QObject]):
    """Оптимизированный контекстный менеджер для блокировки сигналов"""
    # Проверяем, есть ли виджеты для блокировки
    if not widgets:
        yield
        return
        
    # Сохраняем текущее состояние и блокируем сигналы
    states = [(w, w.blockSignals(True)) for w in widgets]
    try:
        yield
    finally:
        # Восстанавливаем предыдущее состояние
        for widget, state in states:
            widget.blockSignals(state) 