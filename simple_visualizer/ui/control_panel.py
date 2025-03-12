import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QLabel, QPushButton, QCheckBox, QScrollArea,
                               QColorDialog, QGridLayout, QListWidget, QListWidgetItem)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from simple_visualizer.ui.widgets.performance_monitor import PerformanceMonitor
from simple_visualizer.ui.widgets.legend_item import LegendItem
from simple_visualizer.utils.qt_helpers import block_signals


class ControlPanel(QWidget):
    """
    Панель управления для настройки параметров визуализации
    """

    # Сигналы
    visibilityChanged = Signal(str, bool)
    colorChanged = Signal(str, tuple)
    objectSelected = Signal(str)
    resetViewRequested = Signal()
    screenshotRequested = Signal()
    objectDeleted = Signal(str)

    def __init__(self, parent=None):
        """Инициализация панели управления"""
        super().__init__(parent)
        self.logger = logging.getLogger("simple_visualizer.ui.control_panel")

        # Создаем основной макет
        self.main_layout = QVBoxLayout(self)

        # Создаем скроллируемую область
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)

        # Настраиваем интерфейс
        self._create_ui()

        # Добавляем скроллируемую область в основной макет
        self.main_layout.addWidget(self.scroll_area)

        # Создаем словарь для хранения виджетов легенды
        self.legend_items = {}

        self.logger.info("Панель управления инициализирована")

    def _create_ui(self):
        """Создает пользовательский интерфейс панели управления"""
        self.logger.debug("Создание пользовательского интерфейса панели управления")

        # Создаем группу для информации
        self._create_info_group()

        # Создаем группу для управления камерой
        self._create_camera_group()

        # Создаем группу для управления объектами
        self._create_objects_group()

        # Создаем группу для мониторинга производительности
        self._create_performance_group()

    def _create_info_group(self):
        """Создает группу с информацией"""
        group = QGroupBox("Информация")
        layout = QVBoxLayout()

        # Добавляем метки
        self.info_label = QLabel("Простой визуализатор 3D объектов")
        self.stats_label = QLabel("Объектов: 0")

        layout.addWidget(self.info_label)
        layout.addWidget(self.stats_label)

        group.setLayout(layout)
        self.scroll_layout.addWidget(group)

    def _create_camera_group(self):
        """Создает группу для управления камерой"""
        group = QGroupBox("Камера")
        layout = QVBoxLayout()

        # Кнопка сброса вида
        reset_view_btn = QPushButton("Сбросить вид")
        reset_view_btn.clicked.connect(self.resetViewRequested.emit)

        # Кнопка для снимка экрана
        screenshot_btn = QPushButton("Сохранить снимок")
        screenshot_btn.clicked.connect(self.screenshotRequested.emit)

        layout.addWidget(reset_view_btn)
        layout.addWidget(screenshot_btn)

        group.setLayout(layout)
        self.scroll_layout.addWidget(group)

    def _create_objects_group(self):
        """Создает группу для управления объектами"""
        group = QGroupBox("Объекты")
        layout = QVBoxLayout()

        # Список объектов
        self.object_list = QListWidget()
        self.object_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.object_list.setMinimumHeight(150)
        layout.addWidget(self.object_list)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        # Кнопка для выбора цвета
        color_button = QPushButton("Изменить цвет")
        color_button.clicked.connect(self._on_color_button_clicked)
        buttons_layout.addWidget(color_button)

        # Кнопка обновления
        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(self.force_refresh_objects)
        buttons_layout.addWidget(refresh_button)

        # Кнопка обновления
        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self.remove_object)
        buttons_layout.addWidget(delete_button)

        # Добавляем в основной макет
        layout.addLayout(buttons_layout)

        # Статистика
        self.stats_label = QLabel("Объектов: 0")
        layout.addWidget(self.stats_label)

        # Устанавливаем макет для группы
        group.setLayout(layout)
        self.scroll_layout.addWidget(group)

    def remove_object(self):
        selected_items = self.object_list.selectedItems()
        if not selected_items:
            return

        # Получаем виджет элемента легенды
        item = selected_items[0]
        legend_widget = self.object_list.itemWidget(item)
        if not legend_widget:
            return

        object_name = legend_widget.object_name

        self.object_list.takeItem(self.object_list.row(item))
        self.objectDeleted.emit(object_name)

    def _create_performance_group(self):
        """Создает группу для мониторинга производительности"""
        group = QGroupBox("Производительность")
        layout = QVBoxLayout()

        # Создаем монитор производительности
        self.performance_monitor = PerformanceMonitor()

        layout.addWidget(self.performance_monitor)

        group.setLayout(layout)
        self.scroll_layout.addWidget(group)

    def update_object_list(self, objects: dict):
        """Обновляет список объектов"""
        self.object_list.clear()

        for name, obj in objects.items():
            # Создаем виджет для объекта
            legend_widget = LegendItem(
                name,
                obj.color,
                obj.visible,
            )

            # Создаем элемент списка
            item = QListWidgetItem()
            item.setSizeHint(legend_widget.sizeHint())

            # Добавляем в список
            self.object_list.addItem(item)
            self.object_list.setItemWidget(item, legend_widget)

            # Подключаем сигналы
            legend_widget.visibilityChanged.connect(
                lambda n, v: self.visibilityChanged.emit(n, v)
            )

    def _on_color_button_clicked(self):
        """Обработчик нажатия на кнопку выбора цвета"""
        # Получаем выбранный элемент
        selected_items = self.object_list.selectedItems()
        if not selected_items:
            return

        # Получаем виджет элемента легенды
        item = selected_items[0]
        legend_widget = self.object_list.itemWidget(item)
        if not legend_widget:
            return

        object_name = legend_widget.object_name

        # Открываем диалог выбора цвета
        color = QColorDialog.getColor(QColor(0, 170, 170, 255), self, "Выберите цвет")

        if color.isValid():
            # Преобразуем QColor в кортеж (r, g, b, a) в формате float
            color_tuple = (
                color.red() / 255.0,
                color.green() / 255.0,
                color.blue() / 255.0,
                color.alpha() / 255.0
            )

            # Обновляем цвет в легенде
            legend_widget.set_color(color_tuple)

            # Отправляем сигнал
            self.colorChanged.emit(object_name, color_tuple)

    def update_object_color(self, object_name, color):
        """
        Обновляет цвет объекта в легенде

        Args:
            object_name: Имя объекта
            color: Новый цвет (r, g, b, a)
        """
        if object_name in self.legend_items:
            self.legend_items[object_name].set_color(color)

    def update_object_visibility(self, object_name, visible):
        """
        Обновляет видимость объекта в легенде

        Args:
            object_name: Имя объекта
            visible: Новая видимость
        """
        if object_name in self.legend_items:
            self.legend_items[object_name].set_visibility(visible)

    def debug_visibility_changed(self, name, visible):
        """Отладочный обработчик изменения видимости"""
        print(f"[PANEL] Сигнал изменения видимости для '{name}': {visible}")
        # Просто передаем сигнал дальше
        self.visibilityChanged.emit(name, visible)

    def force_refresh_objects(self):
        """
        Принудительно обновляет отображение всех объектов
        """
        print("[PANEL] Принудительное обновление всех объектов")
        for name, legend_item in self.legend_items.items():
            # Эмулируем пользовательское изменение видимости
            # только для видимых объектов (с установленным чекбоксом)
            if legend_item.visibility_checkbox.isChecked():
                print(f"[PANEL] Принудительное обновление объекта '{name}'")
                self.visibilityChanged.emit(name, True)

    def _on_selection_changed(self):
        """Обработчик изменения выбора объекта в списке"""
        selected_items = self.object_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            legend_widget = self.object_list.itemWidget(item)
            if legend_widget:
                print(f"[PANEL] Выбран объект '{legend_widget.object_name}'")
                self.objectSelected.emit(legend_widget.object_name)

    def update_object_count(self, objects):
        self.stats_label.setText(f"Объектов: {len(objects)}")

    def select_object(self, object_name):
        """Выделяет объект в списке по его имени"""
        self.logger.debug(f"Выделение объекта '{object_name}' в легенде")

        # Отменяем текущее выделение
        self.object_list.clearSelection()

        # Ищем объект в списке и выделяем его
        for i in range(self.object_list.count()):
            item = self.object_list.item(i)
            legend_widget = self.object_list.itemWidget(item)

            if legend_widget and legend_widget.object_name == object_name:
                # Блокируем сигналы, чтобы избежать рекурсивного вызова
                with block_signals(self.object_list):
                    item.setSelected(True)
                    self.object_list.scrollToItem(item)
                break
