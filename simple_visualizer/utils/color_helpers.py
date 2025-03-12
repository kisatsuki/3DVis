from PySide6.QtGui import QColor
from typing import Tuple

from PySide6.QtWidgets import QColorDialog


def qcolor_to_tuple(color: QColor) -> Tuple[float, float, float, float]:
    """Преобразует QColor в кортеж (r, g, b, a) в диапазоне [0, 1]"""
    return (
        color.red() / 255.0,
        color.green() / 255.0, 
        color.blue() / 255.0,
        color.alpha() / 255.0
    )

def tuple_to_qcolor(color_tuple: Tuple[float, float, float, float]) -> QColor:
    """Преобразует кортеж (r, g, b, a) в диапазоне [0, 1] в QColor"""
    return QColor(
        int(color_tuple[0] * 255),
        int(color_tuple[1] * 255),
        int(color_tuple[2] * 255),
        int(color_tuple[3] * 255)
    )

def show_color_dialog(parent, current_color=None):
    """Показывает диалог выбора цвета и возвращает результат"""
    if current_color is None:
        qcolor = QColor(128, 128, 128, 255)
    elif isinstance(current_color, tuple):
        qcolor = tuple_to_qcolor(current_color)
    else:
        qcolor = current_color
    
    color = QColorDialog.getColor(
        qcolor, 
        parent, 
        "Выберите цвет",
        QColorDialog.ShowAlphaChannel
    )
    
    if color.isValid():
        return color
    return None 