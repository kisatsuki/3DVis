from PySide6.QtWidgets import (QWidget, QHBoxLayout, QCheckBox,
                               QLabel, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap
from simple_visualizer.utils.qt_helpers import block_signals


class ColorIndicator(QLabel):
    """Виджет для отображения цвета объекта"""

    def __init__(self, color=(0.5, 0.5, 0.5, 1.0), parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.color = color
        self._update_color()

    def set_color(self, color):
        """Устанавливает цвет индикатора"""
        self.color = color
        self._update_color()

    def _update_color(self):
        """Обновляет отображение цвета"""
        pixmap = QPixmap(16, 16)
        qcolor = QColor(
            int(self.color[0] * 255),
            int(self.color[1] * 255),
            int(self.color[2] * 255),
            int(self.color[3] * 255)
        )
        pixmap.fill(qcolor)
        self.setPixmap(pixmap)


class LegendItem(QWidget):
    """Элемент легенды для списка объектов"""

    # Сигналы
    visibilityChanged = Signal(str, bool)  # имя объекта, видимость

    def __init__(self, object_name, color=(0.5, 0.5, 0.5, 1.0), visible=True, parent=None):
        super().__init__(parent)
        self.object_name = object_name

        # Создаем основной макет
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 2, 4, 2)

        # Создаем стандартный чекбокс
        self.visibility_checkbox = QCheckBox()
        self.visibility_checkbox.setChecked(visible)

        # Цветовой индикатор
        self.color_indicator = ColorIndicator(color)

        # Надпись с именем объекта
        self.name_label = QLabel(object_name)
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Добавляем виджеты в макет
        self.layout.addWidget(self.visibility_checkbox)
        self.layout.addWidget(self.color_indicator)
        self.layout.addWidget(self.name_label)

        # Важно! Переопределяем обработчик стандартного события клика
        self.visibility_checkbox.clicked.connect(self._on_checkbox_clicked)

        # Устанавливаем начальное состояние без сигнала
        self.set_visibility_no_signal(visible)

    def set_color(self, color):
        """Устанавливает цвет индикатора"""
        self.color = color
        # self._update_color()

    def set_visibility(self, visible):
        """Устанавливает состояние чекбокса видимости"""
        # Проверяем, отличается ли текущее состояние
        if self.visibility_checkbox.isChecked() != visible:
            self.visibility_checkbox.setChecked(visible)

    def set_visibility_no_signal(self, visible):
        """Устанавливает состояние чекбокса без генерации сигнала"""
        with block_signals(self.visibility_checkbox):
            self.visibility_checkbox.setChecked(visible)

    def _on_checkbox_clicked(self, checked):
        """Прямой обработчик клика по чекбоксу (вместо stateChanged)"""
        self.visibilityChanged.emit(self.object_name, checked)

    def mousePressEvent(self, event):
        """Обработка клика мыши по всему элементу легенды"""
        # Если клик был по чекбоксу, позволяем ему обработать событие
        checkbox_rect = self.visibility_checkbox.geometry()
        if checkbox_rect.contains(event.pos()):
            super().mousePressEvent(event)
            return

        # Находим QListWidgetItem, который содержит этот виджет
        parent = self.parent()
        if parent and hasattr(parent, 'setSelected'):
            parent.setSelected(True)

        super().mousePressEvent(event)
