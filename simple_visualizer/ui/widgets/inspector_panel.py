from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout,
                               QLineEdit, QDoubleSpinBox, QCheckBox, QPushButton,
                               QLabel, QColorDialog, QSizePolicy, QDialog,
                               QHBoxLayout, QGridLayout)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QColor
from ..dialogs.script_editor import ScriptEditorDialog
import logging
from simple_visualizer.utils.color_helpers import qcolor_to_tuple, tuple_to_qcolor, show_color_dialog
from simple_visualizer.utils.qt_helpers import block_signals


class InspectorPanel(QWidget):
    """Панель инспектора объектов"""

    transformChanged = Signal(str, dict)  # name, transform_data
    colorChanged = Signal(str, tuple)  # name, color
    visibilityChanged = Signal(str, bool)  # name, visible
    scriptChanged = Signal(str, str, str)  # name, move_script, rotation_script
    requestObjectData = Signal(str)  # name -> запрос данных объекта
    requestAnimationState = Signal(str)  # name -> запрос состояния анимации
    runScriptRequested = Signal(str)  # name -> запрос запуска анимации
    stopScriptRequested = Signal(str)  # name -> запрос остановки анимации
    playableChanged = Signal(str, bool)  # name, is_playable
    physicsChanged = Signal(str, dict)  # name, physics_data
    object_changed = Signal(str, dict)  # name, data

    def __init__(self, parent=None):
        """Инициализация панели инспектора объектов"""
        super().__init__(parent)
        self.logger = logging.getLogger("simple_visualizer.ui.widgets.inspector_panel")
        
        # Инициализируем UI
        self._init_ui()
        
        # Инициализируем кэш значений
        self._last_values = {
            'position': (0, 0, 0),
            'rotation': (0, 0, 0),
            'scale': (1, 1, 1)
        }
        
        # Группируем спинбоксы после их создания
        self.transform_spinboxes = {
            'position': (self.pos_x, self.pos_y, self.pos_z),
            'rotation': (self.rot_x, self.rot_y, self.rot_z),
            'scale': (self.scale_x, self.scale_y, self.scale_z)
        }
        
        # Устанавливаем более редкие обновления для спинбоксов
        for spinboxes in self.transform_spinboxes.values():
            for spinbox in spinboxes:
                spinbox.setKeyboardTracking(False)  # Обновление только при завершении ввода
        
        self.current_object = None
        self.pending_updates = {}
        
        # Создаем таймер для буферизации обновлений
        self.update_timer = QTimer()
        self.update_timer.setInterval(16)  # ~60 FPS
        self.update_timer.timeout.connect(self._process_buffered_updates)

    def _init_ui(self):
        """Инициализация UI элементов"""
        layout = QVBoxLayout(self)
        
        # Основной макет
        self.layout = layout
        self.layout.setContentsMargins(4, 4, 4, 4)

        # Заголовок
        self.header = QLabel("Инспектор")
        self.header.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.header)

        # Создаем группы параметров
        self._create_transform_group()
        self._create_appearance_group()

        # Группа анимации
        self.animation_group = QGroupBox("Анимация")
        animation_layout = QGridLayout()

        # Поля для скриптов
        animation_layout.addWidget(QLabel("Движение:"), 0, 0)
        self.move_script_field = QLineEdit()
        self.move_script_field.setReadOnly(True)
        self.move_script_field.setPlaceholderText("Нет скрипта")
        animation_layout.addWidget(self.move_script_field, 0, 1)

        animation_layout.addWidget(QLabel("Вращение:"), 1, 0)
        self.rotation_script_field = QLineEdit()
        self.rotation_script_field.setReadOnly(True)
        self.rotation_script_field.setPlaceholderText("Нет скрипта")
        animation_layout.addWidget(self.rotation_script_field, 1, 1)

        # Кнопки для скриптов
        buttons_layout = QHBoxLayout()

        self.script_button = QPushButton("Добавить скрипт")
        self.script_button.clicked.connect(self._on_script_button_clicked)
        buttons_layout.addWidget(self.script_button)

        self.animation_button = QPushButton("Запустить")
        self.animation_button.clicked.connect(self._on_animation_button_clicked)
        buttons_layout.addWidget(self.animation_button)

        animation_layout.addLayout(buttons_layout, 2, 0, 1, 2)

        self.animation_group.setLayout(animation_layout)
        self.layout.addWidget(self.animation_group)

        # Добавляем группу управления TODO я пока убрал играбельность
        self.control_group = QGroupBox("Управление")
        control_layout = QVBoxLayout()

        # Флажок играбельности
        self.playable_checkbox = QCheckBox("Играбельный объект")
        self.playable_checkbox.stateChanged.connect(self._on_playable_changed)
        control_layout.addWidget(self.playable_checkbox)

        # Описание управления
        control_info = QLabel(
            "Управление:\n"
            "WASD - перемещение\n"
            "Space - вверх\n"
            "Shift - вниз"
        )
        control_layout.addWidget(control_info)

        # self.control_group.setLayout(control_layout)
        # self.layout.addWidget(self.control_group)

        # Добавляем группу физики
        physics_group = QGroupBox("Физика")
        physics_layout = QVBoxLayout()

        # Чекбокс для включения физики
        self.physics_checkbox = QCheckBox("Физическое тело")
        physics_layout.addWidget(self.physics_checkbox)

        # Чекбокс для статичности
        self.static_checkbox = QCheckBox("Статичный объект")
        physics_layout.addWidget(self.static_checkbox)

        # Подключаем сигналы
        self.physics_checkbox.stateChanged.connect(self._on_physics_changed)
        self.static_checkbox.stateChanged.connect(self._on_static_changed)

        physics_group.setLayout(physics_layout)
        self.layout.addWidget(physics_group)

        # Добавляем растягивающийся виджет в конец
        self.layout.addStretch()

        # По умолчанию все элементы управления неактивны
        self.setEnabled(False)

    def _create_transform_group(self):
        """Создает группу параметров трансформации"""
        group = QGroupBox("Трансформация")
        layout = QFormLayout()

        # Позиция
        self.pos_x = self._create_spin_box()
        self.pos_y = self._create_spin_box()
        self.pos_z = self._create_spin_box()
        layout.addRow("X:", self.pos_x)
        layout.addRow("Y:", self.pos_y)
        layout.addRow("Z:", self.pos_z)

        # Масштаб
        self.scale_x = self._create_spin_box(default=1.0, minimum=0.01)
        self.scale_y = self._create_spin_box(default=1.0, minimum=0.01)
        self.scale_z = self._create_spin_box(default=1.0, minimum=0.01)
        layout.addRow("Масштаб X:", self.scale_x)
        layout.addRow("Масштаб Y:", self.scale_y)
        layout.addRow("Масштаб Z:", self.scale_z)

        # Поворот
        self.rot_x = self._create_spin_box(maximum=360)
        self.rot_y = self._create_spin_box(maximum=360)
        self.rot_z = self._create_spin_box(maximum=360)
        layout.addRow("Поворот X:", self.rot_x)
        layout.addRow("Поворот Y:", self.rot_y)
        layout.addRow("Поворот Z:", self.rot_z)

        group.setLayout(layout)
        self.layout.addWidget(group)

    def _create_appearance_group(self):
        """Создает группу параметров внешнего вида"""
        group = QGroupBox("Внешний вид")
        layout = QFormLayout()

        # Видимость
        self.visibility = QCheckBox()
        self.visibility.setChecked(True)
        self.visibility.stateChanged.connect(self._on_visibility_changed)
        layout.addRow("Видимость:", self.visibility)

        # Кнопка выбора цвета
        self.color_button = QPushButton("Выбрать цвет")
        self.color_button.clicked.connect(self._on_color_button_clicked)
        layout.addRow("Цвет:", self.color_button)

        group.setLayout(layout)
        self.layout.addWidget(group)

    def _create_spin_box(self, minimum=-1000, maximum=1000, default=0.0):
        """Создает спин-бокс с заданными параметрами"""
        spin_box = QDoubleSpinBox()
        spin_box.setRange(minimum, maximum)
        spin_box.setValue(default)
        spin_box.setSingleStep(0.1)
        spin_box.valueChanged.connect(self._on_transform_changed)
        return spin_box

    def set_object(self, name: str):
        """Устанавливает текущий объект для инспектора"""
        if self.current_object != name:  # Меняем объект только если он действительно изменился
            self.logger.debug(f"Смена объекта в инспекторе: {name}")
            self.current_object = name
            if name:
                # Запрашиваем данные только если объект действительно изменился
                self.requestObjectData.emit(name)
                self.requestAnimationState.emit(name)
                self._set_controls_enabled(True)
            else:
                self._set_controls_enabled(False)

    def _clear_fields(self):
        """Очищает все поля инспектора"""
        # Очищаем поля трансформации
        for spinbox in [self.pos_x, self.pos_y, self.pos_z,
                        self.rot_x, self.rot_y, self.rot_z,
                        self.scale_x, self.scale_y, self.scale_z]:
            spinbox.setValue(0.0)

        # Очищаем поля видимости и играбельности
        self.visibility.setChecked(False)
        self.playable_checkbox.setChecked(False)

        # Очищаем поля скриптов
        self.move_script_field.clear()
        self.rotation_script_field.clear()

        # Сбрасываем состояние кнопки анимации
        self.animation_button.setText("Запустить анимацию")

        # Очищаем состояния физики
        self.physics_checkbox.setChecked(False)
        self.static_checkbox.setChecked(False)

        # Очищаем заголовок
        self.header.setText("Инспектор")

    def update_object_data(self, name: str, data: dict):
        if name != self.current_object:
            return
        
        self.pending_updates = data  # Сохраняем последнее обновление
        if not self.update_timer.isActive():
            self.update_timer.start()

    def _process_buffered_updates(self):
        if self.pending_updates:
            # Применяем накопленные обновления
            self._apply_updates(self.pending_updates)
            self.pending_updates = {}

    def _apply_updates(self, data: dict):
        """Обновляет данные объекта только если это текущий выбранный объект"""
        if not self.current_object:
            return

        self.logger.debug(f"Обновление данных для текущего объекта: {self.current_object}")
        self.logger.debug(f"Полученные данные: {data}")  # Добавляем вывод данных

        # Список всех виджетов, сигналы которых нужно блокировать
        widgets = [
            self.pos_x, self.pos_y, self.pos_z,
            self.rot_x, self.rot_y, self.rot_z,
            self.scale_x, self.scale_y, self.scale_z,
            self.visibility, self.playable_checkbox,
            self.move_script_field, self.rotation_script_field,
            self.physics_checkbox, self.static_checkbox
        ]

        # Используем контекстный менеджер для блокировки сигналов
        with block_signals(*widgets):
            # Обновляем трансформацию
            if 'transform' in data:
                transform = data['transform']
                # Позиция
                if 'position' in transform:
                    self.pos_x.setValue(transform['position'][0])
                    self.pos_y.setValue(transform['position'][1])
                    self.pos_z.setValue(transform['position'][2])
                # Вращение
                if 'rotation' in transform:
                    self.rot_x.setValue(transform['rotation'][0])
                    self.rot_y.setValue(transform['rotation'][1])
                    self.rot_z.setValue(transform['rotation'][2])
                # Масштаб
                if 'scale' in transform:
                    self.scale_x.setValue(transform['scale'][0])
                    self.scale_y.setValue(transform['scale'][1])
                    self.scale_z.setValue(transform['scale'][2])

            # Обновляем видимость
            if 'visible' in data:
                self.visibility.setChecked(data['visible'])

            # Обновляем скрипты анимации
            if 'animation' in data:
                animation = data['animation']
                self.move_script_field.setText(animation.get('move_script', ''))
                self.rotation_script_field.setText(animation.get('rotation_script', ''))

            # Обновляем состояние играбельности
            if 'playable' in data:
                self.playable_checkbox.setChecked(data['playable'])

            # Обновляем состояние физики
            if 'physics' in data:
                self.logger.debug(f"Обновление физики из данных: {data['physics']}")  # Добавляем лог
                self.physics_checkbox.setChecked(data['physics']['enabled'])
                self.static_checkbox.setChecked(data['physics']['is_static'])

    def _on_transform_changed(self):
        """Обработчик изменения параметров трансформации"""
        if not self.current_object:
            return

        transform_data = {
            'position': (self.pos_x.value(), self.pos_y.value(), self.pos_z.value()),
            'scale': (self.scale_x.value(), self.scale_y.value(), self.scale_z.value()),
            'rotation': (self.rot_x.value(), self.rot_y.value(), self.rot_z.value())
        }

        self.transformChanged.emit(self.current_object, transform_data)

    def _on_visibility_changed(self, state):
        """Обработчик изменения видимости"""
        if self.current_object:
            self.visibilityChanged.emit(self.current_object, bool(state))

    def _on_color_button_clicked(self):
        """Обработчик кнопки выбора цвета"""
        if not self.current_object:
            return

        # Получаем текущий цвет в формате QColor
        current_color = self.color_button.property("current_color")

        # Открываем диалог выбора цвета
        color = show_color_dialog(self, current_color)

        # Если пользователь выбрал цвет
        if color:
            # Обновляем цвет кнопки
            self._update_color_button(color)

            # Преобразуем QColor в кортеж (r, g, b, a)
            color_tuple = qcolor_to_tuple(color)

            # Отправляем сигнал об изменении цвета
            self.colorChanged.emit(self.current_object, color_tuple)

    def _on_script_button_clicked(self):
        """Обработчик кнопки добавления скрипта"""
        self._on_edit_script()

    def _on_animation_button_clicked(self):
        """Обработчик кнопки анимации"""
        if self.current_object:
            # Определяем текущее состояние по тексту кнопки
            is_running = self.animation_button.text() == "Остановить"

            if is_running:
                self.stopScriptRequested.emit(self.current_object)
            else:
                self.runScriptRequested.emit(self.current_object)

    def _on_playable_changed(self, state):
        """Обработчик изменения состояния играбельности"""
        if self.current_object:
            self.playableChanged.emit(self.current_object, bool(state))

    def _on_physics_changed(self, state):
        """Обработчик изменения состояния физики"""
        if not self.current_object:
            return

        self.logger.debug(f"Изменение физики для {self.current_object}: {state}")
        physics_data = {
            'enabled': self.physics_checkbox.isChecked(),
            'is_static': self.static_checkbox.isChecked()
        }
        self.physicsChanged.emit(self.current_object, physics_data)

    def _on_static_changed(self, state):
        """Обработчик изменения статичности объекта"""
        if not self.current_object:
            return

        self.logger.debug(f"Изменение статичности для {self.current_object}: {state}")
        physics_data = {
            'enabled': self.physics_checkbox.isChecked(),
            'is_static': self.static_checkbox.isChecked()
        }
        self.physicsChanged.emit(self.current_object, physics_data)

    def _set_controls_enabled(self, enabled):
        """Включает/выключает элементы управления"""
        # Включаем сам виджет
        self.setEnabled(enabled)

        # Включаем все элементы управления
        self.pos_x.setEnabled(enabled)
        self.pos_y.setEnabled(enabled)
        self.pos_z.setEnabled(enabled)
        self.scale_x.setEnabled(enabled)
        self.scale_y.setEnabled(enabled)
        self.scale_z.setEnabled(enabled)
        self.rot_x.setEnabled(enabled)
        self.rot_y.setEnabled(enabled)
        self.rot_z.setEnabled(enabled)
        self.visibility.setEnabled(enabled)
        self.color_button.setEnabled(enabled)
        self.animation_group.setEnabled(enabled)
        self.playable_checkbox.setEnabled(enabled)
        self.script_button.setEnabled(enabled)
        self.animation_button.setEnabled(enabled)
        self.physics_checkbox.setEnabled(enabled)
        self.static_checkbox.setEnabled(enabled)

    def set_animation_running(self, is_running: bool):
        """Обновляет состояние кнопки анимации"""
        if not self.current_object:
            return

        self.animation_button.setText(
            "Остановить" if is_running else "Запустить"
        )

    def _on_edit_script(self):
        """Открывает редактор скриптов"""
        if not self.current_object:
            return

        # Получаем текущие скрипты и настройки
        move_script = self.move_script_field.text()
        rotation_script = self.rotation_script_field.text()
        use_relative = self.obj_data['animation'].get('use_relative', False)  # Получаем текущее значение

        # Создаем диалог редактора
        dialog = ScriptEditorDialog(
            rotation_script=rotation_script,
            move_script=move_script,
            use_relative=use_relative,  # Передаем значение
            parent=self
        )

        if dialog.exec() == QDialog.Accepted:
            scripts = dialog.get_scripts()
            self.move_script_field.setText(scripts['move'])
            self.rotation_script_field.setText(scripts['rotation'])

            # Сохраняем все скрипты и настройки
            self.scriptChanged.emit(
                self.current_object,
                scripts['move'],
                scripts['rotation']
            )

            # Обновляем данные объекта
            if self.obj_data:
                self.obj_data['animation']['move_script'] = scripts['move']
                self.obj_data['animation']['rotation_script'] = scripts['rotation']
                self.obj_data['animation']['use_relative'] = scripts['use_relative']  # Сохраняем настройку

    def set_object_data(self, name: str, data: dict):
        """Устанавливает данные объекта в инспектор"""
        if name != self.current_object:
            self.logger.debug(f"Пропуск установки данных для {name} (текущий: {self.current_object})")
            return

        self.logger.debug(f"Установка данных для объекта: {name}")
        self.obj_data = data  # Сохраняем данные объекта

        # Список всех виджетов, сигналы которых нужно блокировать
        widgets = [
            self.pos_x, self.pos_y, self.pos_z,
            self.rot_x, self.rot_y, self.rot_z,
            self.scale_x, self.scale_y, self.scale_z,
            self.visibility, self.playable_checkbox,
            self.move_script_field, self.rotation_script_field,
            self.physics_checkbox, self.static_checkbox
        ]

        # Используем контекстный менеджер для блокировки сигналов
        with block_signals(*widgets):
            # Заголовок
            self.header.setText(f"Инспектор: {name}")

            # Трансформация
            position = data['transform']['position']
            rotation = data['transform']['rotation']
            scale = data['transform']['scale']

            # Устанавливаем значения для каждой группы координат
            for i, widget in enumerate([self.pos_x, self.pos_y, self.pos_z]):
                widget.setValue(position[i])

            for i, widget in enumerate([self.rot_x, self.rot_y, self.rot_z]):
                widget.setValue(rotation[i])

            for i, widget in enumerate([self.scale_x, self.scale_y, self.scale_z]):
                widget.setValue(scale[i])

            # Видимость
            self.visibility.setChecked(data['visible'])

            # Цвет
            qcolor = tuple_to_qcolor(data['color'])
            # self._update_color_button(qcolor)

            # Анимация
            self.move_script_field.setText(data['animation']['move_script'])
            self.rotation_script_field.setText(data['animation']['rotation_script'])

            # Играбельность
            self.playable_checkbox.setChecked(data['playable'])

            # Физика - обновляем только для текущего объекта
            self.physics_checkbox.setChecked(data['physics']['enabled'])
            self.static_checkbox.setChecked(data['physics']['is_static'])

            # Включаем сам виджет
            self._set_controls_enabled(True)

    def update_transform(self, name: str, transform_data: tuple):
        """Оптимизированное обновление трансформации"""
        if name != self.current_object:
            return
            
        position, rotation, scale = transform_data
        transform_values = {
            'position': position,
            'rotation': rotation,
            'scale': scale
        }
        
        # Блокируем сигналы всех спинбоксов одновременно
        all_spinboxes = [box for boxes in self.transform_spinboxes.values() for box in boxes]
        with block_signals(*all_spinboxes):
            # Обновляем значения только если они изменились
            for transform_type, value in transform_values.items():
                if value != self._last_values[transform_type]:
                    self._last_values[transform_type] = value
                    for i, spinbox in enumerate(self.transform_spinboxes[transform_type]):
                        if abs(spinbox.value() - value[i]) > 1e-6:  # Проверяем существенность изменения
                            spinbox.setValue(value[i])
