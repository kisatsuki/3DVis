import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from PySide6.QtCore import QObject, Signal

from ..object3d import Object3D, Mesh3D, Points3D, Line3D
from ..simple_shapes import (
    create_cube, create_sphere, create_torus,
    create_cone, create_floor, create_cylinder
)


class ObjectManager(QObject):
    """
    Менеджер объектов сцены.
    Отвечает за создание, удаление и управление 3D объектами.
    """

    # Сигналы
    object_added = Signal(str)  # name
    object_removed = Signal(str)  # name
    object_updated = Signal(str, dict)  # name, data
    object_visibility_changed = Signal(str, bool)  # name, visible
    object_color_changed = Signal(str, tuple)  # name, color
    object_geometry_changed = Signal(str)  # name
    object_transform_changed = Signal(str, dict)  # name, transform_data

    def __init__(self, viewport=None):
        """
        Инициализация менеджера объектов

        Args:
            viewport: Опциональный viewport для визуализации
        """
        super().__init__()
        self.logger = logging.getLogger("simple_visualizer.core.managers.object_manager")
        self.objects: Dict[str, Object3D] = {}
        self.viewport = viewport

        # Словарь доступных фигур
        self.available_shapes = {
            'cube': create_cube,
            'sphere': create_sphere,
            'cylinder': create_cylinder,
            'torus': create_torus,
            'cone': create_cone,
            'floor': create_floor,
        }

    def set_viewport(self, viewport):
        """
        Устанавливает viewport для визуализации

        Args:
            viewport: Объект viewport
        """
        self.viewport = viewport
        # Пересоздаем все объекты в новом viewport
        for obj in self.objects.values():
            obj.create_view_item(viewport)

    def add_mesh(self, name: str, vertices: np.ndarray, faces: np.ndarray,
                color: Tuple[float, float, float, float] = (0, 0.7, 0.7, 1.0),
                visible: bool = True) -> bool:
        """
        Добавляет меш в сцену

        Args:
            name: Имя объекта
            vertices: Вершины меша
            faces: Индексы граней
            color: Цвет меша (r, g, b, a)
            visible: Видимость по умолчанию

        Returns:
            bool: True если объект успешно добавлен
        """
        try:
            # Создаем объект меша
            mesh = Mesh3D(name, vertices, faces, color, visible)

            # Подключаем сигналы
            self._connect_object_signals(mesh)

            # Добавляем в словарь объектов
            self.objects[name] = mesh

            # Если есть viewport, создаем визуальное представление
            if self.viewport:
                mesh.create_view_item(self.viewport)

            self.object_added.emit(name)
            self.logger.info(f"Меш '{name}' успешно добавлен")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении меша '{name}': {e}")
            return False

    def add_points(self, name: str, points: np.ndarray, size: int = 5,
                  color: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0),
                  visible: bool = True) -> bool:
        """
        Добавляет точки в сцену

        Args:
            name: Имя объекта
            points: Координаты точек
            size: Размер точек
            color: Цвет точек (r, g, b, a)
            visible: Видимость по умолчанию

        Returns:
            bool: True если объект успешно добавлен
        """
        try:
            # Создаем объект точек
            points_obj = Points3D(name, points, size, color, visible)

            # Подключаем сигналы
            self._connect_object_signals(points_obj)

            # Добавляем в словарь объектов
            self.objects[name] = points_obj

            # Если есть viewport, создаем визуальное представление
            if self.viewport:
                points_obj.create_view_item(self.viewport)

            self.object_added.emit(name)
            self.logger.info(f"Точки '{name}' успешно добавлены")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении точек '{name}': {e}")
            return False

    def add_line(self, name: str, points: np.ndarray, width: int = 1,
                color: Tuple[float, float, float, float] = (0.0, 1.0, 0.0, 1.0),
                visible: bool = True) -> bool:
        """
        Добавляет линию в сцену

        Args:
            name: Имя объекта
            points: Точки линии
            width: Ширина линии
            color: Цвет линии (r, g, b, a)
            visible: Видимость по умолчанию

        Returns:
            bool: True если объект успешно добавлен
        """
        try:
            # Создаем объект линии
            line = Line3D(name, points, width, color, visible)

            # Подключаем сигналы
            self._connect_object_signals(line)

            # Добавляем в словарь объектов
            self.objects[name] = line

            # Если есть viewport, создаем визуальное представление
            if self.viewport:
                line.create_view_item(self.viewport)

            self.object_added.emit(name)
            self.logger.info(f"Линия '{name}' успешно добавлена")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении линии '{name}': {e}")
            return False

    def remove_object(self, name: str) -> bool:
        """
        Удаляет объект из сцены

        Args:
            name: Имя объекта

        Returns:
            bool: True если объект успешно удален
        """
        if name not in self.objects:
            self.logger.warning(f"Объект '{name}' не найден")
            return False

        try:
            # Получаем объект
            obj = self.objects[name]

            # Удаляем из viewport
            if self.viewport:
                obj.remove_from_viewport(self.viewport)

            # Удаляем из словаря объектов
            del self.objects[name]

            self.object_removed.emit(name)
            self.logger.info(f"Объект '{name}' успешно удален")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при удалении объекта '{name}': {e}")
            return False

    def clear(self):
        """Удаляет все объекты из сцены"""
        # Удаляем все объекты из viewport
        if self.viewport:
            for obj in self.objects.values():
                obj.remove_from_viewport(self.viewport)

        # Очищаем словарь объектов
        self.objects.clear()

    def get_object_data(self, name: str) -> Optional[dict]:
        """
        Возвращает данные объекта

        Args:
            name: Имя объекта

        Returns:
            Optional[dict]: Словарь с данными объекта или None
        """
        if name not in self.objects:
            return None

        return self.objects[name].to_dict()

    def set_visibility(self, name: str, visible: bool) -> bool:
        """
        Устанавливает видимость объекта

        Args:
            name: Имя объекта
            visible: Флаг видимости

        Returns:
            bool: True если видимость успешно установлена
        """
        if name not in self.objects:
            return False

        try:
            obj = self.objects[name]
            obj.visible = visible

            if self.viewport:
                self.viewport.set_visibility(name, visible)

            self.object_visibility_changed.emit(name, visible)
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при изменении видимости объекта '{name}': {e}")
            return False

    def set_color(self, name: str, color: Tuple[float, float, float, float]) -> bool:
        """
        Устанавливает цвет объекта

        Args:
            name: Имя объекта
            color: Новый цвет (r, g, b, a)

        Returns:
            bool: True если цвет успешно установлен
        """
        if name not in self.objects:
            return False

        try:
            obj = self.objects[name]
            obj.color = color

            if self.viewport:
                self.viewport.update_object_color(name, color)

            self.object_color_changed.emit(name, color)
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при изменении цвета объекта '{name}': {e}")
            return False

    def update_geometry(self, name: str, vertices=None, faces=None) -> bool:
        """
        Обновляет геометрию объекта

        Args:
            name: Имя объекта
            vertices: Новые вершины
            faces: Новые индексы граней

        Returns:
            bool: True если геометрия успешно обновлена
        """
        if name not in self.objects:
            return False

        try:
            obj = self.objects[name]

            if vertices is not None:
                obj.vertices = vertices
            if faces is not None:
                obj.faces = faces

            if self.viewport:
                obj.recreate_view_item(self.viewport)

            self.object_geometry_changed.emit(name)
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении геометрии объекта '{name}': {e}")
            return False

    def create_primitive(self, primitive_type: str, name: str = None, **kwargs) -> Optional[str]:
        """
        Создает примитивный объект

        Args:
            primitive_type: Тип примитива ('cube', 'sphere', etc.)
            name: Имя объекта (опционально)
            **kwargs: Дополнительные параметры для создания примитива

        Returns:
            Optional[str]: Имя созданного объекта или None в случае ошибки
        """
        if primitive_type not in self.available_shapes:
            self.logger.error(f"Неизвестный тип примитива: {primitive_type}")
            return None

        try:
            # Генерируем имя, если не указано
            if name is None:
                name = f"{primitive_type}_{len(self.objects) + 1}"

            # Создаем геометрию
            vertices, faces = self.available_shapes[primitive_type](**kwargs)

            # Добавляем объект
            if self.add_mesh(name, vertices, faces):
                return name

        except Exception as e:
            self.logger.error(f"Ошибка при создании примитива '{primitive_type}': {e}")

        return None

    def _connect_object_signals(self, obj: Object3D):
        """
        Подключает сигналы объекта к менеджеру

        Args:
            obj: Объект для подключения сигналов
        """
        obj.visibility_changed.connect(
            lambda name, visible: self.object_visibility_changed.emit(name, visible))
        obj.color_changed.connect(
            lambda name, color: self.object_color_changed.emit(name, color))
        obj.geometry_changed.connect(
            lambda name: self.object_geometry_changed.emit(name))
        obj.transform_changed.connect(
            lambda name, transform: self.object_transform_changed.emit(name, transform)) 