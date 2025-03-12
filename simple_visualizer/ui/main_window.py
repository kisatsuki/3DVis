import logging
import os

import numpy as np
from PySide6.QtWidgets import (QMainWindow, QSplitter, QStatusBar,
                               QFileDialog, QMessageBox, QMenu, QToolBar, QDialog, QVBoxLayout, QTextEdit, QPushButton)
from PySide6.QtCore import Qt, QSettings, QSize
from PySide6.QtGui import QAction, QIcon, QFont
from pathlib import Path

from simple_visualizer.core.viewport import Viewport3D
from simple_visualizer.core.scene_manager import SceneManager
from simple_visualizer.core.simple_shapes import create_cube, create_sphere, create_torus, create_cone, create_cylinder, \
    create_floor
from simple_visualizer.ui.control_panel import ControlPanel
from simple_visualizer.ui.dialogs.script_editor import ScriptEditorDialog
from simple_visualizer.ui.widgets.inspector_panel import InspectorPanel

np.seterr(divide='ignore', invalid='ignore')


class MainWindow(QMainWindow):
    """
    Главное окно приложения визуализации
    """

    def __init__(self):
        """Инициализация главного окна"""
        super().__init__()

        # Настраиваем логирование
        self.logger = logging.getLogger("simple_visualizer.ui.main_window")
        self.logger.setLevel(logging.DEBUG)  # Устанавливаем уровень DEBUG

        # Настройка окна
        self.setWindowTitle("Simple Visualizer")
        self.resize(1200, 800)

        # Создаем компоненты
        self._init_components()
        self._create_ui()
        self._setup_connections()

        # Загружаем настройки
        self._load_settings()

        # Загружаем последнее состояние
        self._load_last_state()

        self.debug_colliders = False  # Добавляем флаг для отображения коллайдеров

        self.logger.info("Главное окно инициализировано")

    def _init_components(self):
        """Инициализирует основные компоненты"""
        self.logger.debug("Инициализация компонентов")

        # Создаем менеджер сцены
        self.scene_manager = SceneManager()

        # Подключаем сигнал обновления объекта
        self.scene_manager.object_updated.connect(self._on_object_updated)

        # Создаем вьюпорт для 3D
        self.viewport = Viewport3D()

        # Подключаем сигналы физического движка к вьюпорту
        if hasattr(self.scene_manager, 'physics_engine'):
            self.scene_manager.physics_engine.collider_updated.connect(
                self.viewport.update_collider
            )

        # Устанавливаем вьюпорт в менеджер сцены
        self.scene_manager.set_viewport(self.viewport)

        # Создаем панель управления
        self.control_panel = ControlPanel()

        # Создаем инспектор
        self.inspector = InspectorPanel()
        
        # Подключаем сигнал профилирования
        self.scene_manager.profiling_stats.connect(self._show_profiling_stats)

    def _create_ui(self):
        """Создает пользовательский интерфейс"""
        self.logger.debug("Создание пользовательского интерфейса")

        # Создаем разделитель для главного окна
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        # Добавляем виджеты в разделитель
        self.splitter.addWidget(self.control_panel)
        self.splitter.addWidget(self.viewport)
        self.splitter.addWidget(self.inspector)

        # Получаем общую ширину окна
        total_width = self.width()

        # Устанавливаем начальные размеры (20% : 60% : 20%)
        left_panel_width = int(total_width * 0.2)
        viewport_width = int(total_width * 0.6)
        inspector_width = int(total_width * 0.2)

        self.splitter.setSizes([left_panel_width, viewport_width, inspector_width])

        # Запрещаем схлопывание боковых панелей до нуля
        self.splitter.setCollapsible(0, False)  # Левая панель
        self.splitter.setCollapsible(2, False)  # Инспектор

        # Создаем статус-бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готов")

        # Создаем меню и панель инструментов
        self._create_menu()
        self._create_toolbar()

    def _create_menu(self):
        """Создает главное меню"""
        menubar = self.menuBar()

        # Меню File
        file_menu = menubar.addMenu('Файл')

        load_action = QAction('Загрузить сцену...', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self._on_load_scene)
        file_menu.addAction(load_action)

        load_test_action = QAction('Загрузить тестовую сцену', self)
        load_test_action.setShortcut('Ctrl+T')
        load_test_action.triggered.connect(self._on_load_test_scene)
        file_menu.addAction(load_test_action)

        # Меню Animation
        animation_menu = menubar.addMenu('Анимация')

        start_all_action = QAction('Запустить все анимации', self)
        start_all_action.setShortcut('Ctrl+Shift+P')
        start_all_action.triggered.connect(self._on_start_all_animations)
        animation_menu.addAction(start_all_action)

        stop_all_action = QAction('Остановить все анимации', self)
        stop_all_action.setShortcut('Ctrl+Shift+S')
        stop_all_action.triggered.connect(self._on_stop_all_animations)
        animation_menu.addAction(stop_all_action)

        # Меню Debug
        debug_menu = menubar.addMenu('Отладка')

        # Действие для включения/выключения LOD
        self.toggle_lod_action = QAction('Показать уровни детализации', self)
        self.toggle_lod_action.setCheckable(True)
        self.toggle_lod_action.setShortcut('Ctrl+L')
        self.toggle_lod_action.triggered.connect(self._on_toggle_lod)
        debug_menu.addAction(self.toggle_lod_action)

        # Добавляем действие для профилирования
        self.toggle_profiling_action = QAction("Профилирование анимаций", self)
        self.toggle_profiling_action.setCheckable(True)
        self.toggle_profiling_action.triggered.connect(self._on_toggle_profiling)
        debug_menu.addAction(self.toggle_profiling_action)

        # Действие для переключения отображения коллайдеров
        self.toggle_colliders_action = QAction('Отображать хитбоксы', self)
        self.toggle_colliders_action.setShortcut('Ctrl+K')
        self.toggle_colliders_action.setCheckable(True)
        self.toggle_colliders_action.triggered.connect(self._on_toggle_colliders)
        debug_menu.addAction(self.toggle_colliders_action)

        # Действие: Сохранить снимок
        save_screenshot_action = QAction("Сохранить снимок", self)
        save_screenshot_action.triggered.connect(self._save_screenshot)
        file_menu.addAction(save_screenshot_action)

        # Разделитель
        file_menu.addSeparator()

        # Действие: Выход
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Вид
        view_menu = menubar.addMenu("Вид")

        # Действие: Сбросить камеру
        reset_view_action = QAction("Сбросить камеру", self)
        reset_view_action.triggered.connect(self._reset_view)
        view_menu.addAction(reset_view_action)

        # Меню Объекты
        objects_menu = menubar.addMenu("Объекты")

        # Подменю: Добавить объект
        add_object_menu = QMenu("Добавить объект", self)

        # Действия для добавления объектов
        add_cube_action = QAction("Куб", self)
        add_cube_action.triggered.connect(self._add_cube)
        add_object_menu.addAction(add_cube_action)

        add_sphere_action = QAction("Сфера", self)
        add_sphere_action.triggered.connect(self._add_sphere)
        add_object_menu.addAction(add_sphere_action)

        add_torus_action = QAction("Тор", self)
        add_torus_action.triggered.connect(self._add_torus)
        add_object_menu.addAction(add_torus_action)

        add_cone_action = QAction("Конус", self)
        add_cone_action.triggered.connect(self._add_cone)
        add_object_menu.addAction(add_cone_action)

        add_cylinder_action = QAction("Цилиндр", self)
        add_cylinder_action.triggered.connect(self._add_cylinder)
        add_object_menu.addAction(add_cylinder_action)

        add_floor_action = QAction("Пол", self)
        add_floor_action.triggered.connect(self._add_floor)
        add_object_menu.addAction(add_floor_action)

        objects_menu.addMenu(add_object_menu)

        # Действие: Очистить сцену
        clear_scene_action = QAction("Очистить сцену", self)
        clear_scene_action.triggered.connect(self._clear_scene)
        objects_menu.addAction(clear_scene_action)

    def _create_toolbar(self):
        """Создает панель инструментов"""
        # Создаем панель инструментов
        toolbar = QToolBar("Основная панель")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Добавляем действия
        reset_view_action = QAction("Сбросить камеру", self)
        reset_view_action.triggered.connect(self._reset_view)
        toolbar.addAction(reset_view_action)

        # Разделитель
        toolbar.addSeparator()

        # Действия для объектов
        add_cube_action = QAction("Куб", self)
        add_cube_action.triggered.connect(self._add_cube)
        toolbar.addAction(add_cube_action)

        add_sphere_action = QAction("Сфера", self)
        add_sphere_action.triggered.connect(self._add_sphere)
        toolbar.addAction(add_sphere_action)

        # Разделитель
        toolbar.addSeparator()

        # Действие для очистки сцены
        clear_scene_action = QAction("Очистить", self)
        clear_scene_action.triggered.connect(self._clear_scene)
        toolbar.addAction(clear_scene_action)

    def _setup_connections(self):
        """Устанавливает связи между сигналами и слотами"""
        # Связи с инспектором
        self.inspector.transformChanged.connect(
            lambda name, data: self.scene_manager.set_transform(name, **data)
        )
        self.inspector.colorChanged.connect(
            lambda name, color: self.scene_manager.set_color(name, color)
        )
        self.inspector.visibilityChanged.connect(
            lambda name, visible: self.scene_manager.set_visibility(name, visible)
        )
        self.inspector.scriptChanged.connect(
            lambda name, move, rot: self.scene_manager.set_object_script(name, move, rot)
        )
        self.inspector.runScriptRequested.connect(
            lambda name: self.scene_manager.run_animation(name)
        )
        self.inspector.stopScriptRequested.connect(
            lambda name: self.scene_manager.stop_animation(name)
        )
        self.inspector.playableChanged.connect(
            lambda name, state: self.scene_manager.make_object_playable(name, state)
        )
        self.inspector.requestAnimationState.connect(self._on_request_animation_state)

        # Связь с SceneManager для отслеживания состояния анимации
        self.scene_manager.animation_state_changed.connect(self._on_animation_state_changed)
        self.scene_manager.animation_error_occurred.connect(self._on_animation_error)

        # Связи с панелью управления
        self.control_panel.objectSelected.connect(self._on_object_selected)
        self.control_panel.objectDeleted.connect(self._on_object_deleted)
        self.control_panel.visibilityChanged.connect(
            lambda name, visible: self.scene_manager.set_visibility(name, visible)
        )

        # Соединяем сигналы инспектора
        self.inspector.requestObjectData.connect(self._on_request_object_data)

        # Связываем сигнал выбора объекта из вьюпорта
        self.viewport.object_selected.connect(self._on_object_selected)

        # Подключаем обновление инспектора при анимации
        self.scene_manager.object_updated.connect(self.inspector.update_object_data)

        # Подключаем сигнал изменения физики
        self.inspector.physicsChanged.connect(self.scene_manager.set_physics_params)

    def _on_object_visibility_changed(self, object_name, visible):
        """Обработчик изменения видимости объекта"""
        self.logger.debug(f"Видимость объекта '{object_name}' изменена на {visible}")

        # Обновляем видимость объекта через менеджер сцены
        success = self.scene_manager.set_visibility(object_name, visible)

        if not success:
            # Если операция не удалась, возвращаем виджет в предыдущее состояние
            self.control_panel.update_object_visibility(object_name, not visible)
            return

        # Обновляем состояние видимости в инспекторе, если это текущий объект
        if self.inspector.current_object == object_name:
            self.inspector.set_visibility(visible)

    def _on_object_color_changed(self, object_name, color):
        """Обработчик изменения цвета объекта"""
        self.logger.debug(f"Изменение цвета объекта '{object_name}': {color}")

        if self.scene_manager.set_color(object_name, color):
            # Обновляем цвет в легенде
            self.control_panel.update_object_color(object_name, color)
            self.statusBar.showMessage(f"Цвет объекта '{object_name}' изменен")
        else:
            self.statusBar.showMessage(f"Не удалось изменить цвет объекта '{object_name}'")

    # После добавления или удаления объекта:
    def _on_scene_changed(self):
        """Обработчик изменения сцены"""
        # Обновляем список объектов в панели управления
        self.control_panel.update_object_list(self.scene_manager.objects)

    # Также нужно добавить вызов update_object_visibility в методы, 
    # которые изменяют видимость объектов через менеджер сцены

    def _reset_view(self):
        """Сбрасывает позицию камеры"""
        if self.viewport:
            self.viewport.reset_view()
            self.statusBar.showMessage("Камера сброшена")

    def _save_screenshot(self):
        """Сохраняет снимок экрана"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Сохранить снимок", "", "Изображения (*.png *.jpg)"
            )
            if filename:
                self.viewport.save_screenshot(filename)
                self.statusBar.showMessage(f"Снимок сохранен: {filename}")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении снимка: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить снимок: {e}")

    def _add_cube(self):
        """Добавляет куб в сцену"""
        try:
            # Создаем уникальное имя
            name = f"Куб_{len(self.scene_manager.objects) + 1}"

            # Создаем куб
            vertices, faces = create_cube(size=2.0)

            # Добавляем в менеджер сцены
            self.scene_manager.add_mesh(name, vertices, faces)

            # Обновляем панель управления
            self.control_panel.update_object_list(self.scene_manager.objects)

            self.statusBar.showMessage(f"Добавлен объект: {name}")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении куба: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить куб: {e}")

    def _add_sphere(self):
        """Добавляет сферу в сцену"""
        try:
            # Создаем уникальное имя
            name = f"Сфера_{len(self.scene_manager.objects) + 1}"

            # Создаем сферу
            vertices, faces = create_sphere(radius=1.5, resolution=20)

            # Добавляем в менеджер сцены
            self.scene_manager.add_mesh(name, vertices, faces, color=(0.7, 0.3, 0.3, 1.0))

            # Обновляем панель управления
            self.control_panel.update_object_list(self.scene_manager.objects)

            self.statusBar.showMessage(f"Добавлен объект: {name}")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении сферы: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить сферу: {e}")

    def _add_torus(self):
        """Добавляет тор в сцену"""
        try:
            # Создаем уникальное имя
            name = f"Тор_{len(self.scene_manager.objects) + 1}"

            # Создаем тор
            vertices, faces = create_torus(major_radius=1.5, minor_radius=0.5, resolution=20)

            # Добавляем в менеджер сцены
            self.scene_manager.add_mesh(name, vertices, faces, color=(0.3, 0.7, 0.3, 1.0))

            # Обновляем панель управления
            self.control_panel.update_object_list(self.scene_manager.objects)

            self.statusBar.showMessage(f"Добавлен объект: {name}")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении тора: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить тор: {e}")

    def _add_cylinder(self):
        """Добавляет цилиндр в сцену"""
        try:
            # Создаем уникальное имя
            name = f"Цилиндр_{len(self.scene_manager.objects) + 1}"

            # Создаем тор
            vertices, faces = create_cylinder()

            # Добавляем в менеджер сцены
            self.scene_manager.add_mesh(name, vertices, faces, color=(0.3, 0.7, 0.3, 1.0))

            # Обновляем панель управления
            self.control_panel.update_object_list(self.scene_manager.objects)

            self.statusBar.showMessage(f"Добавлен объект: {name}")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении цилиндра: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить цилиндр: {e}")

    def _add_floor(self):
        """Добавляет цилиндр в сцену"""
        try:
            # Создаем уникальное имя
            name = f"Пол_{len(self.scene_manager.objects) + 1}"

            # Создаем тор
            vertices, faces = create_floor()

            # Добавляем в менеджер сцены
            self.scene_manager.add_mesh(name, vertices, faces, color=(0.5, 0.5, 0.5, 1.0))

            # Обновляем панель управления
            self.control_panel.update_object_list(self.scene_manager.objects)

            self.statusBar.showMessage(f"Добавлен объект: {name}")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении пола: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить пол: {e}")

    def _add_cone(self):
        """Добавляет конус в сцену"""
        try:
            # Создаем уникальное имя
            name = f"Конус_{len(self.scene_manager.objects) + 1}"

            # Создаем конус
            vertices, faces = create_cone(radius=1.0, height=2.0, resolution=20)

            # Добавляем в менеджер сцены
            self.scene_manager.add_mesh(name, vertices, faces, color=(0.3, 0.3, 0.7, 1.0))

            # Обновляем панель управления
            self.control_panel.update_object_list(self.scene_manager.objects)

            self.statusBar.showMessage(f"Добавлен объект: {name}")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении конуса: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить конус: {e}")

    def _clear_scene(self):
        """Очищает сцену"""
        reply = QMessageBox.question(
            self, "Очистить сцену", "Вы уверены, что хотите удалить все объекты?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.scene_manager.clear()
            self.control_panel.update_object_list({})
            self.statusBar.showMessage("Сцена очищена")

    def _load_settings(self):
        """Загружает настройки приложения"""
        settings = QSettings("SimpleVisualizer", "App")
        self.restoreGeometry(settings.value("geometry", bytes(), type=bytes))
        self.restoreState(settings.value("windowState", bytes(), type=bytes))
        self.splitter.restoreState(settings.value("splitterState", bytes(), type=bytes))

    def _save_settings(self):
        """Сохраняет настройки приложения"""
        settings = QSettings("SimpleVisualizer", "App")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("splitterState", self.splitter.saveState())

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        self.logger.info("Закрытие приложения")

        # Останавливаем все анимации
        for name in self.scene_manager.get_running_animations():
            self.scene_manager.stop_animation(name)
        
        # Сохраняем сцену
        self.scene_manager.save_scene()
        
        # Сохраняем настройки
        self._save_settings()

        # Закрываем окно
        super().closeEvent(event)

    def _on_object_selected(self, object_name):
        """Обработчик выбора объекта"""
        # Получаем данные объекта из менеджера сцены
        if object_name:
            object_data = self.scene_manager.get_object_data(object_name)
            if object_data:
                # Обновляем инспектор с актуальными данными
                self.inspector.set_object(object_name)
                self.inspector.set_object_data(object_name, object_data)

                # Обновляем выделение в панели управления
                self.control_panel.select_object(object_name)

                self.scene_manager.highlight_object(object_name, True)
        else:
            # Если объект не выбран, очищаем инспектор
            self.inspector.set_object(None)

    def _on_object_deleted(self, object_name):
        """Обработчик выбора объекта"""
        if self.scene_manager.viewport and self.scene_manager.viewport.selected_object:
            # Снимаем подсветку с предыдущего объекта
            self.scene_manager.remove_object(object_name)

        # Устанавливаем новый выбранный объект в инспекторе TODO говнище
        if self.inspector.current_object == object_name:
            self.inspector.set_object(None)

    def _on_transform_changed(self, object_name, transform_data):
        """Обработчик изменения трансформации объекта"""
        if self.scene_manager.set_object_transform(object_name, transform_data):
            self.statusBar.showMessage(f"Трансформация объекта '{object_name}' обновлена")
        else:
            self.statusBar.showMessage(f"Не удалось обновить трансформацию '{object_name}'")

    def _on_selection_cleared(self):
        """Обработчик очистки выделения"""
        if self.scene_manager.viewport and self.scene_manager.viewport.selected_object:
            self.scene_manager.highlight_object(
                self.scene_manager.viewport.selected_object,
                False
            )

    def _on_script_changed(self, object_name, move_script, rotation_script):
        """Обработчик изменения скрипта объекта"""
        if self.scene_manager.set_object_script(object_name, move_script, rotation_script):
            self.statusBar.showMessage(f"Скрипт для объекта '{object_name}' обновлен")
        else:
            self.statusBar.showMessage(f"Не удалось обновить скрипт для '{object_name}'")

    def _on_request_object_data(self, name: str):
        """Обработчик запроса данных объекта для инспектора"""
        data = self.scene_manager.get_object_data(name)
        self.inspector.update_object_data(name, data)

    def _on_run_script(self, object_name):
        """Обработчик запуска анимации"""
        if self.scene_manager.run_animation(object_name):
            self.statusBar.showMessage(f"Анимация для '{object_name}' запущена")
        else:
            self.inspector.set_animation_running(False)
            self.statusBar.showMessage(f"Не удалось запустить анимацию для '{object_name}'")

    def _on_stop_script(self, object_name):
        """Обработчик остановки анимации"""
        if self.scene_manager.stop_animation(object_name):
            self.statusBar.showMessage(f"Анимация для '{object_name}' остановлена")
        else:
            self.statusBar.showMessage(f"Не удалось остановить анимацию для '{object_name}'")

    def _load_last_state(self):
        """Загружает последнее состояние приложения"""
        if self.scene_manager.load_scene():
            self.statusBar.showMessage("Последняя сцена восстановлена")
            # Обновляем список объектов в интерфейсе
            self.control_panel.update_object_list(self.scene_manager.objects)
            # Обновляем статистику
            self.control_panel.update_object_count(self.scene_manager.objects)
            # Сбрасываем инспектор
            self.inspector.set_object(None)
            # Добавлено: обновляем видимость объектов
            for name, obj_data in self.scene_manager.objects.items():
                self.control_panel.update_object_visibility(name, obj_data.visible)
        else:
            self.statusBar.showMessage("Не удалось восстановить последнюю сцену")

    def keyPressEvent(self, event):
        """Обработчик нажатия клавиш"""
        key = event.key()
        print(f"[DEBUG] Key pressed: {key}, text: {event.text().upper()}")

        # Маппинг клавиш (добавляем русские буквы)
        key_map = {
            Qt.Key_W: 'W',
            Qt.Key_A: 'A',
            Qt.Key_S: 'S',
            Qt.Key_D: 'D',
            Qt.Key_Space: 'Space',
            Qt.Key_Shift: 'Shift',
            # Русские клавиши
            1062: 'W',  # Ц
            1060: 'A',  # Ф
            1067: 'S',  # Ы
            1042: 'D',  # В
        }

        if key in key_map:
            print(f"[DEBUG] Moving with key: {key_map[key]}")
            self.scene_manager.handle_key_press(key_map[key])

        if event.key() == Qt.Key_L:  # Клавиша L
            # Переключаем режим отображения LOD
            self.viewport.debug_lod = not getattr(self.viewport, 'debug_lod', False)
            mode = "включен" if self.viewport.debug_lod else "выключен"
            self.statusBar.showMessage(f"Режим отладки LOD {mode}")

        # Вызываем родительский обработчик
        super().keyPressEvent(event)

    def _on_animation_state_changed(self, object_name: str, is_running: bool):
        """Обработчик изменения состояния анимации"""
        if self.inspector.current_object == object_name:
            self.inspector.animation_button.setText(
                "Остановить" if is_running else "Запустить"
            )

    def _on_load_scene(self):
        """Обработчик загрузки сцены"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить сцену",
            "",
            "JSON files (*.json)"
        )
        if file_path:
            # Конвертируем строку в Path
            self.scene_manager.scene_file = Path(file_path)
            if self.scene_manager.load_scene():
                self.control_panel.update_object_list(self.scene_manager.objects)
                self.statusBar.showMessage(f"Сцена загружена: {file_path}")
            else:
                self.statusBar.showMessage("Ошибка при загрузке сцены")

    def _on_load_test_scene(self):
        """Обработчик загрузки тестовой сцены"""
        test_scene_path = Path("test_scene.json")
        if test_scene_path.exists():
            self.scene_manager.scene_file = test_scene_path
            if self.scene_manager.load_scene():
                self.control_panel.update_object_list(self.scene_manager.objects)
                self.statusBar.showMessage("Тестовая сцена загружена")
            else:
                self.statusBar.showMessage("Ошибка при загрузке тестовой сцены")
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Файл тестовой сцены не найден"
            )

    def _on_start_all_animations(self):
        """Запускает все анимации в сцене"""
        count = 0
        for name, obj in self.scene_manager.objects.items():
            # Проверяем наличие скриптов анимации
            move_script = obj.animation['move_script']
            rotation_script = obj.animation['rotation_script']

            # Запускаем анимацию, если есть хотя бы один скрипт
            if move_script or rotation_script:
                if self.scene_manager.run_animation(name):
                    count += 1
                    if name == self.inspector.current_object:
                        self.inspector.set_animation_running(True)

        self.statusBar.showMessage(f"Запущено анимаций: {count}")
        self.logger.info(f"Запущено {count} анимаций")

    def _on_stop_all_animations(self):
        """Останавливает все анимации в сцене"""
        count = 0
        for name in self.scene_manager.get_running_animations():
            if self.scene_manager.stop_animation(name):
                count += 1
                if name == self.inspector.current_object:
                    self.inspector.set_animation_running(False)

        self.statusBar.showMessage(f"Остановлено анимаций: {count}")
        self.logger.info(f"Остановлено {count} анимаций")

    def _on_toggle_lod(self):
        """Обработчик включения/выключения отображения LOD"""
        is_enabled = self.toggle_lod_action.isChecked()
        self.viewport.debug_lod = is_enabled

        # Включаем/выключаем отображение статистики вершин
        if is_enabled:
            # Добавим отладочный вывод
            try:
                self.viewport.vertexStatsUpdated.connect(
                    self.control_panel.performance_monitor.show_vertex_stats
                )
            except Exception as e:
                self.logger.error(f"Ошибка при подключении сигнала: {e}")
        else:
            try:
                self.viewport.vertexStatsUpdated.disconnect(
                    self.control_panel.performance_monitor.show_vertex_stats
                )
            except Exception as e:
                self.logger.error(f"Ошибка при отключении сигнала: {e}")
            self.control_panel.performance_monitor.hide_vertex_stats()

        # Принудительно обновляем LOD для получения первых данных
        self.viewport.update_lods()

        mode = "включен" if is_enabled else "выключен"
        self.statusBar.showMessage(f"Режим отладки LOD {mode}")

    def _on_animation_error(self, object_name, error_message):
        """Обработчик ошибок анимации"""
        self.logger.error(f"Ошибка анимации объекта '{object_name}': {error_message}")
        self.statusBar.showMessage(f"Ошибка анимации: {error_message}", 5000)

        # Если открыт инспектор для этого объекта, обновляем состояние кнопки
        if self.inspector.current_object == object_name:
            self.inspector.set_animation_running(False)

    def _on_request_animation_state(self, name: str):
        """Обработчик запроса состояния анимации"""
        is_running = self.scene_manager.is_animation_running(name)
        self.inspector.set_animation_running(is_running)

    def _on_object_updated(self, name: str, data: dict):
        """Обработчик обновления объекта"""
        # Обновляем только если это текущий выбранный объект
        if self.inspector and self.inspector.current_object == name:
            self.inspector.update_object_data(name, data)
            # self.inspector.update_transform(data.get('transform', {}))

    def _on_toggle_profiling(self):
        """Обработчик включения/выключения профилирования"""
        self.scene_manager.toggle_profiling()
        
    def _show_profiling_stats(self, stats: str):
        """Показывает результаты профилирования"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Результаты профилирования")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier"))
        text_edit.setText(stats)
        layout.addWidget(text_edit)
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.show()

    def stop_all_animations(self):
        """Останавливает все анимации в сцене"""
        count = 0
        for name in self.scene_manager.get_running_animations():
            if self.scene_manager.stop_animation(name):
                count += 1
        return count

    def _on_toggle_colliders(self):
        """Обработчик переключения отображения коллайдеров"""
        self.debug_colliders = self.toggle_colliders_action.isChecked()
        self.viewport.set_debug_colliders(self.debug_colliders)
        
        status = "enabled" if self.debug_colliders else "disabled"
        self.statusBar.showMessage(f"Collider visualization {status}", 2000)