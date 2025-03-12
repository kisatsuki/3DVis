import logging
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal
from math import sin, cos, pi
import copy


class Object3D(QObject):
    """Базовый класс для 3D объектов"""

    # Сигналы для оповещения об изменениях
    transform_changed = Signal(str, dict)  # name, transform_data
    visibility_changed = Signal(str, bool)  # name, is_visible
    color_changed = Signal(str, tuple)  # name, color
    geometry_changed = Signal(str)  # name

    def __init__(self, name: str, color: Tuple[float, float, float, float], visible: bool = True):
        super().__init__()
        self.name = name
        self._color = color
        self._visible = visible
        self._transform = {
            'position': (0, 0, 0),
            'rotation': (0, 0, 0),
            'scale': (1, 1, 1)
        }
        self._animation = {
            'move_script': "",
            'rotation_script': "",
            'enabled': False,
            'use_relative': False
        }
        self._playable = False
        self._selected = False
        self._original_color = color
        self._view_item = None

        # Инициализируем logger
        self.logger = logging.getLogger(f"simple_visualizer.core.object3d.{name}")

        # Добавляем кэш для bounding radius
        self._cached_bounding_radius = None
        self._cached_bounds = None
        self._geometry_changed = True

    @property
    def color(self) -> Tuple[float, float, float, float]:
        """Возвращает цвет объекта"""
        return self._color

    @color.setter
    def color(self, value: Tuple[float, float, float, float]):
        """Устанавливает цвет объекта"""
        self._color = value
        self.color_changed.emit(self.name, value)

    @property
    def visible(self) -> bool:
        """Возвращает видимость объекта"""
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        """Устанавливает видимость объекта"""
        self._visible = value
        self.visibility_changed.emit(self.name, value)

    @property
    def transform(self) -> Dict[str, Tuple[float, float, float]]:
        """Возвращает трансформацию объекта"""
        return self._transform.copy()

    @property
    def position(self) -> Tuple[float, float, float]:
        """Возвращает позицию объекта"""
        return self._transform['position']

    @position.setter
    def position(self, value: Tuple[float, float, float]):
        """Устанавливает позицию объекта"""
        self.set_transform(position=value)

    @property
    def rotation(self) -> Tuple[float, float, float]:
        """Возвращает вращение объекта"""
        return self._transform['rotation']

    @rotation.setter
    def rotation(self, value: Tuple[float, float, float]):
        """Устанавливает вращение объекта"""
        self.set_transform(rotation=value)

    @property
    def scale(self) -> Tuple[float, float, float]:
        """Возвращает масштаб объекта"""
        return self._transform['scale']

    @scale.setter
    def scale(self, value: Tuple[float, float, float]):
        """Устанавливает масштаб объекта"""
        self.set_transform(scale=value)

    @property
    def animation(self) -> Dict[str, Any]:
        """Возвращает параметры анимации"""
        return self._animation.copy()

    @property
    def playable(self) -> bool:
        """Возвращает играбельность объекта"""
        return self._playable

    @playable.setter
    def playable(self, value: bool):
        """Устанавливает играбельность объекта"""
        self._playable = value

    @property
    def selected(self) -> bool:
        """Возвращает выбранность объекта"""
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        """Устанавливает выбранность объекта"""
        if value == self._selected:
            return

        self._selected = value
        # При выборе объекта меняем его цвет
        if value:
            # Сохраняем оригинальный цвет
            self._original_color = self._color
            # Делаем цвет ярче для выделения
            highlight_color = tuple(min(1.0, c * 1.3) for c in self._color[:3]) + (self._color[3],)
            self._color = highlight_color
        else:
            # Возвращаем оригинальный цвет
            self._color = self._original_color

        self.color_changed.emit(self.name, self._color)

    @property
    def physics_enabled(self) -> bool:
        """Этот метод теперь должен получать информацию из физического движка"""
        return False  # По умолчанию физика выключена

    def set_transform(self, position: Optional[Tuple[float, float, float]] = None,
                      rotation: Optional[Tuple[float, float, float]] = None,
                      scale: Optional[Tuple[float, float, float]] = None) -> None:
        """Устанавливает параметры трансформации"""
        has_changes = False

        if position is not None:
            self._transform['position'] = tuple(map(float, position))
            has_changes = True

        if rotation is not None:
            self._transform['rotation'] = tuple(map(float, rotation))
            has_changes = True

        if scale is not None:
            self._transform['scale'] = tuple(map(float, scale))
            has_changes = True

        if has_changes:
            # Отправляем только сигнал об изменении трансформации
            # Не вызываем geometry_changed, так как это не изменение геометрии
            self.transform_changed.emit(self.name, self._transform)

    def set_animation_scripts(self, move_script: str, rotation_script: str) -> None:
        """Устанавливает скрипты анимации"""
        self._animation['move_script'] = move_script
        self._animation['rotation_script'] = rotation_script

    def toggle_visibility(self) -> None:
        """Переключает видимость объекта"""
        self.visible = not self._visible

    def get_type(self) -> str:
        """Возвращает тип объекта"""
        raise NotImplementedError("Должно быть реализовано в подклассах")

    def to_dict(self) -> Dict[str, Any]:
        """Сохраняет объект в словарь"""
        transform_copy = copy.deepcopy(self._transform)
        animation_copy = copy.deepcopy(self._animation)

        # Базовые параметры объекта
        data = {
            'type': self.get_type(),
            'color': self._color,
            'visible': self._visible,
            'transform': transform_copy,
            'animation': animation_copy,
            'playable': self._playable
        }

        return data

    def create_view_item(self, viewport):
        """Создает элемент отображения в вьюпорте"""
        raise NotImplementedError("Должно быть реализовано в подклассах")

    def update_view_item(self, viewport):
        """Обновляет элемент отображения в вьюпорте"""
        if not self._view_item:
            self.create_view_item(viewport)
            return

        # Обновление трансформации
        viewport.set_transform(
            self.name,
            self._transform['position'],
            self._transform['rotation'],
            self._transform['scale']
        )

        # Обновление видимости
        viewport.set_visibility(self.name, self._visible)

    def set_animation_enabled(self, enabled: bool) -> None:
        """Включает/выключает анимацию объекта"""
        self._animation['enabled'] = enabled
        self.logger.debug(f"Анимация {'включена' if enabled else 'выключена'} для объекта {self.name}")

    def update_animation(self, t, dt: float, safe_globals) -> None:
        """
        Обновляет состояние анимации

        Args:
            t: Время, прошедшее с начала
            dt: Время, прошедшее с последнего обновления
        """
        if not self._animation['enabled']:
            return

        try:
            move_code = self.animation['move_script']
            transform_data = {}

            # Выполняем скрипт движения с ограничением времени выполнения
            if move_code:
                local_vars = {'t': t, 'dt': dt, 'result': None}
                exec(move_code, safe_globals, local_vars)
                if 'result' in local_vars and local_vars['result']:
                    self._transform['position'] = local_vars['result']
                    transform_data['position'] = local_vars['result']

            rotation_code = self.animation['rotation_script']

            # Выполняем скрипт вращения
            if rotation_code:
                local_vars = {'t': t, 'dt': dt, 'result': None}
                exec(rotation_code, safe_globals, local_vars)
                if 'result' in local_vars and local_vars['result']:
                    self._transform['rotation'] = local_vars['result']
                    transform_data['rotation'] = local_vars['result']

            # Отправляем сигнал только если были изменения
            if transform_data:
                self.transform_changed.emit(self.name, self._transform)

        except Exception as e:
            self.logger.error(f"Ошибка при выполнении анимации: {e}")
            self._animation['enabled'] = False

    def remove_from_viewport(self, viewport) -> None:
        """Удаляет объект из viewport"""
        if self._view_item and self.name in viewport.view_items:
            viewport.remove_item(self.name)
            self._view_item = None

    def recreate_view_item(self, viewport) -> bool:
        """Пересоздает элемент отображения в viewport"""
        self.remove_from_viewport(viewport)
        self.create_view_item(viewport)
        return self._view_item is not None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Object3D':
        """Создает объект из словаря"""
        kwargs = {
            'name': data['name'],
            'color': data['color'],
            'visible': data['visible']
        }

        # Создаем экземпляр объекта
        obj = cls(**kwargs)

        # Устанавливаем общие атрибуты
        obj._transform = data['transform']
        obj._animation = data['animation']
        obj._playable = data.get('playable', False)

        return obj

    def update_geometry(self):
        """Оповещает об изменении геометрии объекта"""
        self.geometry_changed.emit(self.name)

    def get_animation_data(self) -> dict:
        """Возвращает данные анимации объекта"""
        return self._animation

    def ray_intersect(self, ray_origin, ray_direction):
        """
        Проверяет пересечение луча с объектом
        
        Args:
            ray_origin: Начало луча (x, y, z)
            ray_direction: Направление луча (x, y, z)
            
        Returns:
            float: Расстояние до пересечения или None, если пересечения нет
        """
        # Базовая реализация, должна быть переопределена в подклассах
        return None

    def update_bounds(self):
        """Обновляет границы объекта"""
        if hasattr(self, 'vertices'):
            # Для меша используем реальные вершины
            min_bounds = np.min(self.vertices, axis=0)
            max_bounds = np.max(self.vertices, axis=0)
            return tuple(min_bounds) + tuple(max_bounds)
        else:
            # Для других объектов используем единичный куб
            pos = self.position
            scale = self.scale
            return (
                pos[0] - scale[0], pos[1] - scale[1], pos[2] - scale[2],
                pos[0] + scale[0], pos[1] + scale[1], pos[2] + scale[2]
            )

    def calculate_bounding_radius(self) -> float:
        """Вычисляет радиус ограничивающей сферы"""
        # Используем кэшированное значение, если геометрия не изменилась
        if not self._geometry_changed and self._cached_bounding_radius is not None:
            return self._cached_bounding_radius

        if len(self.vertices) == 0:
            return 0.5

        # Находим центр масс
        center = np.mean(self.vertices, axis=0)

        # Находим максимальное расстояние от центра до вершины
        distances = np.sqrt(np.sum((self.vertices - center) ** 2, axis=1))
        max_distance = np.max(distances)

        # Кэшируем результат
        self._cached_bounding_radius = max_distance
        self._geometry_changed = False
        return max_distance

    def invalidate_cache(self):
        """Инвалидирует кэш при изменении геометрии"""
        self._cached_bounding_radius = None
        self._cached_bounds = None
        self._geometry_changed = True
        self.geometry_changed.emit(self.name)


class Mesh3D(Object3D):
    """Класс для 3D меша"""

    def __init__(self, name: str, vertices: np.ndarray, faces: np.ndarray,
                 color: Tuple[float, float, float, float] = (0, 0.7, 0.7, 1.0),
                 visible: bool = True):
        super().__init__(name, color, visible)
        self.vertices = vertices.copy()
        self.faces = faces.copy()

    def get_type(self) -> str:
        return "mesh"

    def create_view_item(self, viewport):
        """Создает элемент отображения в вьюпорте"""
        success = viewport.add_mesh(self.name, self.vertices, self.faces, self._color)
        if success:
            self._view_item = viewport.view_items.get(self.name)
            viewport.set_visibility(self.name, self._visible)
            viewport.set_transform(
                self.name,
                self._transform['position'],
                self._transform['rotation'],
                self._transform['scale']
            )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для сериализации"""
        data = super().to_dict()
        data.update({
            'vertices': self.vertices.tolist(),
            'faces': self.faces.tolist()
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mesh3D':
        """Создает меш из словаря"""
        # Подготавливаем данные для создания объекта
        name = data.get('name', 'Mesh')
        vertices = np.array(data.get('vertices', []))
        faces = np.array(data.get('faces', []))
        color = data.get('color', (0.7, 0.7, 0.7, 1.0))
        visible = data.get('visible', True)

        # Создаем объект с базовыми параметрами
        mesh = cls(
            name=name,
            vertices=vertices,
            faces=faces,
            color=color,
            visible=visible
        )

        # Устанавливаем дополнительные параметры, если они есть
        if 'transform' in data:
            mesh._transform = data['transform']

        if 'animation' in data:
            mesh._animation = data['animation']

        if 'playable' in data:
            mesh._playable = data['playable']
        else:
            mesh._playable = False

        return mesh

    def set_vertices(self, vertices: np.ndarray):
        """Устанавливает новые вершины"""
        self.vertices = vertices.copy()
        self.invalidate_cache()

    def set_faces(self, faces: np.ndarray):
        """Устанавливает новые грани"""
        self.faces = faces.copy()
        self.invalidate_cache()


class Points3D(Object3D):
    """Класс для точек в 3D пространстве"""

    def __init__(self, name: str, points: np.ndarray, size: int = 5,
                 color: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0),
                 visible: bool = True):
        super().__init__(name, color, visible)
        self.points = points.copy()
        self.size = size

    def get_type(self) -> str:
        return "points"

    def create_view_item(self, viewport):
        """Создает элемент отображения в вьюпорте"""
        success = viewport.add_points(self.name, self.points, self.size, self._color)
        if success:
            self._view_item = viewport.view_items.get(self.name)
            viewport.set_visibility(self.name, self._visible)
            viewport.set_transform(
                self.name,
                self._transform['position'],
                self._transform['rotation'],
                self._transform['scale']
            )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для сериализации"""
        data = super().to_dict()
        data.update({
            'points': self.points.tolist(),
            'size': self.size
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Points3D':
        """Создает точки из словаря"""
        points = np.array(data['points'])
        points_obj = cls(
            name=data['name'],
            points=points,
            size=data['size'],
            color=data['color'],
            visible=data['visible']
        )
        points_obj._transform = data['transform']
        points_obj._animation = data['animation']
        points_obj._playable = data['playable']
        return points_obj


class Line3D(Object3D):
    """Класс для линий в 3D пространстве"""

    def __init__(self, name: str, points: np.ndarray, width: int = 1,
                 color: Tuple[float, float, float, float] = (0.0, 1.0, 0.0, 1.0),
                 visible: bool = True):
        super().__init__(name, color, visible)
        self.points = points.copy()
        self.width = width

    def get_type(self) -> str:
        return "line"

    def create_view_item(self, viewport):
        """Создает элемент отображения в вьюпорте"""
        success = viewport.add_line(self.name, self.points, self.width, self._color)
        if success:
            self._view_item = viewport.view_items.get(self.name)
            viewport.set_visibility(self.name, self._visible)
            viewport.set_transform(
                self.name,
                self._transform['position'],
                self._transform['rotation'],
                self._transform['scale']
            )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для сериализации"""
        data = super().to_dict()
        data.update({
            'points': self.points.tolist(),
            'width': self.width
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Line3D':
        """Создает линию из словаря"""
        # Создаем специальные параметры для Line3D
        kwargs = {
            'name': data['name'],
            'points': np.array(data['points']),
            'width': data.get('width', 1),
            'color': data['color'],
            'visible': data['visible']
        }

        # Создаем экземпляр
        line = cls(**kwargs)

        # Применяем общие атрибуты
        line._transform = data['transform']
        line._animation = data['animation']
        line._playable = data.get('playable', False)

        return line
