import logging
import math
import json
import os
from pathlib import Path

import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Callable
import time
from math import sin, cos  # Для использования в скриптах
import ast
from .animation_thread import AnimationThread
from PySide6.QtCore import QObject, Signal, QTimer
from .object3d import Object3D, Mesh3D, Points3D, Line3D
from simple_visualizer.utils.error_handlers import handle_object_operation
from .simple_shapes import create_cube, create_sphere, create_torus, create_cone, create_floor, create_cylinder
from .physics_engine import PhysicsEngine
from .serialization.scene_serializer import SceneSerializer
from .managers.animation_manager import AnimationManager
from .managers.object_manager import ObjectManager
import cProfile
import pstats
import io
from pstats import SortKey


class SceneManager(QObject):
    """
    Менеджер 3D сцены, управляет объектами и их визуализацией
    """

    animation_state_changed = Signal(str, bool)  # name, is_running
    object_selected = Signal(str)  # name
    animation_error_occurred = Signal(str, str)  # name, error_message
    object_updated = Signal(str, dict)  # name, data
    scene_cleared = Signal()
    object_removed = Signal(str)  # Добавляем сигнал об удалении объекта
    profiling_stats = Signal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("simple_visualizer.core.scene_manager")

        # Инициализируем менеджеры
        self.object_manager = ObjectManager()
        self.scene_serializer = SceneSerializer()
        self.animation_manager = AnimationManager()
        self.physics_engine = PhysicsEngine()

        # Подключаем сигналы анимации
        self.animation_manager.animation_state_changed.connect(self._forward_animation_state_changed)
        self.animation_manager.animation_error_occurred.connect(self._forward_animation_error)
        self.animation_manager.object_updated.connect(self._forward_object_updated)

        # Подключаем сигналы объектов
        self.object_manager.object_added.connect(self._on_object_added)
        self.object_manager.object_removed.connect(self._on_object_removed)
        self.object_manager.object_visibility_changed.connect(self._on_object_visibility_changed)
        self.object_manager.object_color_changed.connect(self._on_object_color_changed)
        self.object_manager.object_geometry_changed.connect(self._on_object_geometry_changed)
        self.object_manager.object_transform_changed.connect(self._on_transform_changed)

        # Изменяем таймер для физической симуляции
        self.physics_timer = QTimer()
        self.physics_timer.timeout.connect(self._update_physics)
        self.physics_timer.start(16)  # 60 FPS
        self.last_physics_update = time.time()

        # Добавляем параметры для профилирования
        self.profiler = cProfile.Profile()
        self.is_profiling = False
        self.profiling_start_time = None
        self.profiling_duration = 5.0  # Длительность профилирования в секундах

        # Параметры для играбельных объектов
        self.playable_object = None
        self.movement_speed = 0.5

    @property
    def objects(self) -> Dict[str, Object3D]:
        """Возвращает словарь объектов"""
        return self.object_manager.objects

    def set_viewport(self, viewport):
        """Устанавливает вьюпорт для визуализации"""
        self.viewport = viewport
        self.object_manager.set_viewport(viewport)

        # Подключаем сигнал трансформации
        self.viewport.object_transformed.connect(self._on_viewport_transform)
        self.logger.info("Вьюпорт установлен")

    def add_mesh(self, name: str, vertices: np.ndarray, faces: np.ndarray,
                 color: Tuple[float, float, float, float] = (0, 0.7, 0.7, 1.0),
                 visible: bool = True) -> bool:
        """Добавляет меш в сцену"""
        return self.object_manager.add_mesh(name, vertices, faces, color, visible)

    def add_points(self, name: str, points: np.ndarray, size: int = 5,
                   color: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0),
                   visible: bool = True) -> bool:
        """Добавляет точки в сцену"""
        return self.object_manager.add_points(name, points, size, color, visible)

    def add_line(self, name: str, points: np.ndarray, width: int = 1,
                 color: Tuple[float, float, float, float] = (0.0, 1.0, 0.0, 1.0),
                 visible: bool = True) -> bool:
        """Добавляет линию в сцену"""
        return self.object_manager.add_line(name, points, width, color, visible)

    def remove_object(self, name: str) -> bool:
        """Удаляет объект из сцены"""
        if name in self.animation_manager.animation_threads:
            self.stop_animation(name)

        if name == self.playable_object:
            self.playable_object = None

        self.physics_engine.unregister_object(name)
        return self.object_manager.remove_object(name)

    def clear(self) -> bool:
        """Очищает сцену"""
        # Останавливаем все анимации
        self.animation_manager.stop_all_animations()

        # Очищаем физический движок
        for name in list(self.objects.keys()):
            self.physics_engine.unregister_object(name)

        # Очищаем объекты
        self.object_manager.clear()

        # Оповещаем об изменениях
        self.scene_cleared.emit()
        self.logger.info("Сцена очищена")
        return True

    def get_object_data(self, name: str) -> Optional[dict]:
        """Возвращает данные объекта"""
        data = self.object_manager.get_object_data(name)
        if data is None:
            return None

        # Добавляем физические параметры
        physics_params = self.physics_engine.get_physics_params(name)
        if physics_params:
            data['physics'] = physics_params
        else:
            data['physics'] = {
                'enabled': False,
                'is_static': True,
                'velocity': [0, 0, 0],
                'acceleration': [0, 0, 0],
                'restitution': 0.5,
                'friction': 0.3
            }

        return data

    def set_transform(self, name: str, position=None, rotation=None, scale=None) -> bool:
        """Устанавливает трансформацию объекта"""
        if name not in self.objects:
            return False

        obj = self.objects[name]
        obj.set_transform(position, rotation, scale)
        return True

    def get_transform(self, name: str) -> Optional[Dict]:
        """Возвращает текущую трансформацию объекта"""
        return self.objects[name].transform

    def set_visibility(self, name: str, visible: bool) -> bool:
        """Устанавливает видимость объекта"""
        return self.object_manager.set_visibility(name, visible)

    def set_color(self, name: str, color: tuple) -> bool:
        """Устанавливает цвет объекта"""
        return self.object_manager.set_color(name, color)

    def highlight_object(self, name: str, highlight: bool = True) -> bool:
        """Подсвечивает объект в сцене"""
        if name not in self.objects:
            return False

        if self.viewport:
            self.viewport.highlight_object(name, highlight)
            return True

        return False

    def set_object_script(self, name: str, move_script: str, rotation_script: str) -> bool:
        """Устанавливает скрипты анимации для объекта"""
        if name not in self.objects:
            return False

        return self.animation_manager.set_object_script(name, self.objects[name], move_script, rotation_script)

    @handle_object_operation()
    def run_animation(self, name: str) -> bool:
        """Запускает анимацию объекта"""
        if name not in self.objects:
            return False

        return self.animation_manager.run_animation(name, self.objects[name])

    @handle_object_operation()
    def stop_animation(self, name: str) -> bool:
        """Останавливает анимацию для объекта"""
        return self.animation_manager.stop_animation(name)

    def is_animation_running(self, name: str) -> bool:
        """Проверяет, запущена ли анимация для объекта"""
        return self.animation_manager.is_animation_running(name)

    def save_scene(self) -> bool:
        """Сохраняет текущее состояние сцены"""
        success, message = self.scene_serializer.save_scene(self.objects)
        if not success:
            self.logger.error(message)
        return success

    def load_scene(self) -> bool:
        """Загружает сцену из файла"""
        # Очищаем текущую сцену
        self.clear()

        # Загружаем данные сцены
        objects_data, message = self.scene_serializer.load_scene()
        if objects_data is None:
            self.logger.error(message)
            return False

        # Загружаем объекты
        loaded_objects = 0
        errors = 0

        for name, obj_data in objects_data.items():
            try:
                # Определяем тип объекта и создаем его
                obj_type = obj_data.get('type')
                if obj_type == 'mesh':
                    if self._load_mesh_object(name, obj_data):
                        loaded_objects += 1
                    else:
                        errors += 1
                elif obj_type == 'points':
                    if self._load_points_object(name, obj_data):
                        loaded_objects += 1
                    else:
                        errors += 1
                elif obj_type == 'line':
                    if self._load_line_object(name, obj_data):
                        loaded_objects += 1
                    else:
                        errors += 1
                else:
                    self.logger.warning(f"Пропускаем объект '{name}': неизвестный тип '{obj_type}'")
                    errors += 1

            except Exception as e:
                self.logger.error(f"Ошибка при создании объекта '{name}': {e}")
                errors += 1

        if loaded_objects > 0:
            self.logger.info(f"Сцена загружена: {loaded_objects} объектов загружено, {errors} ошибок")
            return True
        else:
            self.logger.warning("Не загружено ни одного объекта")
            return False

    def _load_mesh_object(self, name: str, obj_data: dict) -> bool:
        """Загружает меш из данных"""
        if not all(key in obj_data for key in ['vertices', 'faces']):
            self.logger.error(f"Отсутствуют необходимые данные для меша '{name}'")
            return False

        vertices = np.array(obj_data['vertices'])
        faces = np.array(obj_data['faces'])
        color = obj_data.get('color', (0.7, 0.7, 0.7, 1.0))
        visible = obj_data.get('visible', True)

        if self.add_mesh(name, vertices, faces, color, visible):
            self._apply_object_properties(name, obj_data)
            return True
        return False

    def _load_points_object(self, name: str, obj_data: dict) -> bool:
        """Загружает точки из данных"""
        if 'points' not in obj_data:
            self.logger.error(f"Отсутствуют необходимые данные для точек '{name}'")
            return False

        points = np.array(obj_data['points'])
        size = obj_data.get('size', 5)
        color = obj_data.get('color', (1.0, 0.0, 0.0, 1.0))
        visible = obj_data.get('visible', True)

        if self.add_points(name, points, size, color, visible):
            self._apply_object_properties(name, obj_data)
            return True
        return False

    def _load_line_object(self, name: str, obj_data: dict) -> bool:
        """Загружает линию из данных"""
        if 'points' not in obj_data:
            self.logger.error(f"Отсутствуют необходимые данные для линии '{name}'")
            return False

        points = np.array(obj_data['points'])
        width = obj_data.get('width', 1)
        color = obj_data.get('color', (0.0, 1.0, 0.0, 1.0))
        visible = obj_data.get('visible', True)

        if self.add_line(name, points, width, color, visible):
            self._apply_object_properties(name, obj_data)
            return True
        return False

    def _apply_object_properties(self, name: str, obj_data: dict):
        """Применяет дополнительные свойства к объекту"""
        if 'transform' in obj_data:
            self.set_transform(name,
                               obj_data['transform'].get('position'),
                               obj_data['transform'].get('rotation'),
                               obj_data['transform'].get('scale'))

        if 'animation' in obj_data:
            self.set_object_script(name,
                                   obj_data['animation'].get('move_script', ''),
                                   obj_data['animation'].get('rotation_script', ''))

    def _forward_animation_state_changed(self, name: str, is_running: bool):
        """Пересылает сигнал изменения состояния анимации"""
        self.animation_state_changed.emit(name, is_running)

    def _forward_animation_error(self, name: str, error_message: str):
        """Пересылает сигнал ошибки анимации"""
        self.animation_error_occurred.emit(name, error_message)

    def _forward_object_updated(self, name: str, transform_data: dict):
        """Пересылает сигнал обновления объекта"""
        self.object_updated.emit(name, {'transform': transform_data})

    def _on_object_added(self, name: str):
        """Обработчик добавления объекта"""
        self.logger.debug(f"Объект '{name}' добавлен")

    def _on_object_removed(self, name: str):
        """Обработчик удаления объекта"""
        self.object_removed.emit(name)
        self.logger.debug(f"Объект '{name}' удален")

    def _on_object_visibility_changed(self, name: str, visible: bool):
        """Обработчик изменения видимости объекта"""
        if self.viewport:
            self.viewport.set_visibility(name, visible)

    def _on_object_color_changed(self, name: str, color: tuple):
        """Обработчик изменения цвета объекта"""
        if self.viewport:
            self.viewport.update_object_color(name, color)

    def _on_object_geometry_changed(self, name: str):
        """Обработчик изменения геометрии объекта"""
        if name in self.objects and self.viewport:
            obj = self.objects[name]
            # Сохраняем текущую трансформацию
            current_transform = self.objects[name].transform
            # Обновляем геометрию
            obj.recreate_view_item(self.viewport)
            # Восстанавливаем трансформацию
            if current_transform:
                self.viewport.set_transform(name, **current_transform)

    def _on_transform_changed(self, name: str, transform_data: dict):
        """Обработчик изменения трансформации"""
        if name in self.objects and self.viewport:
            # Обновляем трансформацию во вьюпорте без пересоздания объекта
            self.viewport.set_transform(name, **transform_data)
            # Отправляем сигнал об обновлении
            self.object_updated.emit(name, {'transform': transform_data})

    def _update_physics(self):
        """Обновляет физическую симуляцию"""
        self.physics_engine.update()

    def _on_viewport_transform(self, name: str, new_position: tuple):
        """Обработчик изменения трансформации из вьюпорта"""
        if name in self.objects:
            self.set_transform(name, position=new_position)

    def set_physics_params(self, name: str, params: dict):
        """Устанавливает физические параметры объекта"""
        if name in self.objects:
            obj = self.objects[name]

            if params.get('enabled', False):
                self.physics_engine.register_object(obj, params)
            else:
                self.physics_engine.unregister_object(name)

    def get_physics_params(self, name: str) -> Optional[Dict]:
        """Получает физические параметры объекта"""
        return self.physics_engine.get_physics_params(name)

    def is_physics_enabled(self, name: str) -> bool:
        """Проверяет, включена ли физика для объекта"""
        return self.physics_engine.is_physics_enabled(name)

    def make_object_playable(self, name: str, is_playable: bool) -> bool:
        """Устанавливает/снимает играбельность объекта"""
        if name not in self.objects:
            return False

        if is_playable:
            if self.playable_object and self.playable_object != name:
                self.objects[self.playable_object].playable = False
            self.playable_object = name
        else:
            if self.playable_object == name:
                self.playable_object = None

        self.objects[name].playable = is_playable
        return True

    def handle_key_press(self, key: str):
        """Обрабатывает нажатие клавиши для играбельного объекта"""
        if not self.playable_object:
            return

        if self.playable_object not in self.animation_manager.animation_threads:
            return

        obj = self.objects[self.playable_object]
        position = list(obj.position)

        if key == 'W':
            position[0] += self.movement_speed
        elif key == 'S':
            position[0] -= self.movement_speed
        elif key == 'A':
            position[2] -= self.movement_speed
        elif key == 'D':
            position[2] += self.movement_speed
        elif key == 'Space':
            position[1] += self.movement_speed
        elif key == 'Shift':
            position[1] -= self.movement_speed

        self.set_transform(self.playable_object, position=position)

    def get_running_animations(self) -> List[str]:
        """Возвращает список имен объектов с запущенными анимациями"""
        return list(self.animation_manager.animation_threads.keys())

    def toggle_profiling(self):
        """Переключает состояние профилирования"""
        if self.is_profiling:
            self.stop_profiling()
        else:
            self.start_profiling()

    def start_profiling(self):
        """Запускает профилирование анимаций"""
        if not self.is_profiling:
            self.logger.info("Запуск профилирования анимаций")
            self.is_profiling = True
            self.profiling_start_time = time.time()
            self.profiler.enable()

    def stop_profiling(self):
        """Останавливает профилирование и выводит результаты"""
        if self.is_profiling:
            self.profiler.disable()
            self.is_profiling = False

            s = io.StringIO()
            stats = pstats.Stats(self.profiler, stream=s)
            stats.sort_stats(SortKey.CUMULATIVE)
            stats.print_stats(30)

            profiling_stats = s.getvalue()
            self.logger.info("Результаты профилирования:\n%s", profiling_stats)
            self.profiling_stats.emit(profiling_stats)

            self.profiler = cProfile.Profile()
