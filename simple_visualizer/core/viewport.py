import logging
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QSize
from typing import List, Tuple, Dict, Optional
import time

import pyqtgraph.opengl as gl


class Viewport3D(QWidget):
    """
    Упрощенный 3D вьюпорт для визуализации
    """

    # Сигналы
    mouseMoved = Signal(float, float)
    mousePressed = Signal(float, float)
    mouseReleased = Signal(float, float)
    vertexStatsUpdated = Signal(int)  # total_vertices
    object_selected = Signal(str)
    object_transformed = Signal(str, tuple)
    object_thrown = Signal(str, list)  # name, velocity

    def __init__(self, parent=None):
        """Инициализация вьюпорта"""
        super().__init__(parent)
        self.logger = logging.getLogger("simple_visualizer.core.viewport")

        # Создаем основной макет
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Создаем виджет для 3D-просмотра
        self.view = gl.GLViewWidget()
        self.layout.addWidget(self.view)

        # Устанавливаем политики для корректной обработки событий мыши
        self.setFocusPolicy(Qt.StrongFocus)
        self.view.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Добавляем отслеживание событий мыши для GLViewWidget
        self.view.mousePressEvent = self.view_mouse_press_event
        self.view.mouseReleaseEvent = self.view_mouse_release_event
        self.view.mouseMoveEvent = self.view_mouse_move_event

        # Для определения клика vs. перетаскивания
        self.mouse_press_pos = None
        self.drag_threshold = 5  # пикселей
        self.is_dragging = False

        # Для перетаскивания объектов
        self.drag_object_mode = False
        self.drag_start_pos = None
        self.drag_plane_normal = None
        self.drag_plane_point = None
        self.drag_object_initial_pos = None

        # Настраиваем освещение
        self._setup_lighting()

        # Словари для хранения объектов
        self.points = {}
        self.lines = {}
        self.surfaces = {}
        self.items = {}
        self.visibility = {}

        # Настройки камеры
        self.rotation = [30, -45, 0]
        self.translation = [0, 0, -10]
        self.scale = 1.0

        # Состояние мыши
        self.last_pos = None
        self.setMouseTracking(True)

        # Настраиваем базовую сцену
        self.setup_scene()

        self.selected_object = None  # Добавляем отслеживание выделенного объекта
        self.original_colors = {}  # Сохраняем оригинальные цвета

        # Добавляем словарь для хранения данных мешей
        self.mesh_data = {}

        # Добавляем словарь для хранения LOD
        self.mesh_lods: Dict[str, List[Tuple[gl.GLMeshItem, float]]] = {}
        self.current_lod_levels: Dict[str, int] = {}

        # Настройки LOD (более мягкие переходы)
        self.lod_distances = [15.0, 30.0, 45.0]  # Увеличенные дистанции для переключения LOD
        self.lod_ratios = [1.0, 0.7, 0.4]  # Более мягкие коэффициенты упрощения

        self._drag_positions = []  # Список последних позиций при перетаскивании
        self._drag_times = []  # Список времени для каждой позиции
        self._drag_history_length = 5  # Количество сохраняемых позиций для расчета скорости

        # Добавляем отслеживание изменений для оптимизации отрисовки
        self._scene_changed = True
        self._last_frame_time = time.time()
        self._min_frame_time = 1.0 / 60.0  # Максимум 60 FPS

        # Добавляем словарь для хранения визуализации коллайдеров
        self.collider_visualizations = {}
        self.debug_colliders = False

        self.logger.info("Viewport3D инициализирован")

    def _setup_lighting(self):
        """Настраивает освещение сцены"""
        # Устанавливаем положение источника света (сверху сцены)
        self.view.opts['lightPosition'] = (0, 0, 50)  # x, y, z

        # Настраиваем параметры освещения
        self.view.opts.update({
            'lighting': True,  # Включаем освещение
            'ambient': 0.3,  # Уровень фонового освещения
            'diffuse': 0.8,  # Уровень рассеянного света
            'specular': 0.2,  # Уровень бликов
        })

    def setup_scene(self):
        """Настраивает базовые элементы сцены (сетка, оси)"""
        # Добавляем сетку
        self.grid_item = gl.GLGridItem()
        self.grid_item.setSize(x=10, y=10, z=0)
        self.grid_item.setSpacing(x=1, y=1, z=1)
        self.view.addItem(self.grid_item)
        self.logger.debug("Сетка добавлена в сцену")

        # Добавляем оси координат
        self.axes = gl.GLAxisItem()
        self.axes.setSize(x=5, y=5, z=5)
        self.view.addItem(self.axes)
        self.logger.debug("Оси координат добавлены в сцену")

    def add_item(self, item_name, item, type_name):
        """
        Добавляет элемент в сцену
        
        Args:
            item_name: Имя элемента
            item: Объект для добавления
            type_name: Тип объекта
        """
        try:
            self.view.addItem(item)
            self.items[item_name] = {
                'item': item,
                'type': type_name,
                'visible': True
            }
            self.logger.info(f"Добавлен элемент: {item_name} (тип: {type_name})")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении элемента {item_name}: {e}")

    def remove_item(self, name: str) -> bool:
        """Удаляет объект из вьюпорта с очисткой данных"""
        if name in self.view_items:
            try:
                # Получаем объект
                item = self.view_items[name]

                # Удаляем из сцены
                self.view.removeItem(item)

                # Очищаем данные меша
                if name in self.mesh_data:
                    del self.mesh_data[name]

                # Удаляем из словаря
                del self.view_items[name]

                # Удаляем визуализацию коллайдера
                if name in self.collider_visualizations:
                    for item in self.collider_visualizations[name]:
                        self.view.removeItem(item)
                    del self.collider_visualizations[name]

                self.logger.debug(f"Объект '{name}' удален из вьюпорта")
                return True

            except Exception as e:
                self.logger.error(f"Ошибка при удалении объекта '{name}': {e}")
                return False

        return False

    def set_visibility(self, name, visible):
        """
        Устанавливает видимость объекта
        
        Args:
            name: Имя объекта
            visible: Флаг видимости
        
        Returns:
            bool: True, если операция выполнена успешно
        """

        if name in self.view_items:
            item = self.view_items[name]
            try:
                item.setVisible(visible)
                # Принудительно обновляем представление
                self.view.update()
                self.logger.debug(f"Изменена видимость объекта '{name}': {visible}")
                return True

            except Exception as e:
                self.logger.error(f"Ошибка при установке видимости '{name}': {e}")
                return False
        else:
            self.logger.warning(f"Объект '{name}' не найден во вьюпорте")
            return False

    def clear(self):
        """Очищает сцену от всех элементов"""
        try:
            for name in list(self.items.keys()):
                self.remove_item(name)
            # Переустанавливаем базовую сцену
            self.setup_scene()
            self.logger.info("Сцена очищена")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при очистке сцены: {e}")
            return False

    def simplify_mesh(self, vertices: np.ndarray, faces: np.ndarray, target_ratio: float) -> Tuple[
        np.ndarray, np.ndarray]:
        """
        Упрощает меш, уменьшая количество вершин и граней
        
        Args:
            vertices: массив вершин
            faces: массив граней
            target_ratio: целевой коэффициент упрощения (0.0 - 1.0)
        
        Returns:
            Tuple[np.ndarray, np.ndarray]: упрощенные вершины и грани
        """
        if target_ratio >= 1.0:
            return vertices, faces

        # Более мягкое упрощение
        target_faces = max(int(len(faces) * target_ratio), 4)  # Минимум 4 грани

        # Равномерное прореживание с сохранением структуры
        if len(faces) > target_faces:
            step = len(faces) // target_faces
            simplified_faces = faces[::step]
        else:
            simplified_faces = faces

        # Собираем используемые вершины
        used_vertices = np.unique(simplified_faces)
        vertex_map = {old: new for new, old in enumerate(used_vertices)}

        # Создаем новый массив вершин и обновляем индексы
        simplified_vertices = vertices[used_vertices]
        remapped_faces = np.array([[vertex_map[idx] for idx in face] for face in simplified_faces])

        self.logger.debug(
            f"Упрощение меша: исходные вершины: {len(vertices)}, "
            f"грани: {len(faces)} -> новые вершины: {len(simplified_vertices)}, "
            f"грани: {len(remapped_faces)}"
        )

        return simplified_vertices, remapped_faces

    def add_mesh(self, name: str, vertices: np.ndarray, faces: np.ndarray,
                 color: tuple = (0.7, 0.7, 0.7, 1.0)) -> bool:
        """Добавляет меш с поддержкой LOD"""
        try:
            # Создаем разные уровни детализации
            lod_meshes = []
            for ratio in self.lod_ratios:
                # Упрощаем меш для каждого уровня
                lod_vertices, lod_faces = self.simplify_mesh(vertices, faces, ratio)

                # Создаем данные меша
                mesh_data = gl.MeshData(
                    vertexes=lod_vertices.astype(np.float32),
                    faces=lod_faces.astype(np.uint32),
                    vertexColors=None
                )

                # Создаем меш
                mesh_item = gl.GLMeshItem(
                    meshdata=mesh_data,
                    color=color,
                    shader='shaded',
                    glOptions='opaque'
                )

                mesh_item._current_color = color
                mesh_item.setVisible(False)  # Скрываем все уровни кроме первого
                self.view.addItem(mesh_item)

                lod_meshes.append((mesh_item, len(lod_vertices)))

            # Сохраняем все уровни детализации
            self.mesh_lods[name] = lod_meshes
            self.current_lod_levels[name] = 0

            # Показываем первый уровень
            lod_meshes[0][0].setVisible(True)

            # Сохраняем ссылку на текущий активный меш
            if not hasattr(self, 'view_items'):
                self.view_items = {}
            self.view_items[name] = lod_meshes[0][0]

            # Добавляем в общий словарь items
            self.items[name] = {
                'item': lod_meshes[0][0],
                'type': 'mesh',
                'visible': True
            }

            self.logger.debug(f"Добавлен меш '{name}' с {len(self.lod_ratios)} уровнями LOD")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении меша '{name}': {e}")
            return False

    def update_lods(self):
        pass

    def add_points(self, name, points, size=5, color=(0.7, 0.7, 0.7, 1.0)):
        """Добавляет точки в сцену"""
        try:
            # Создаем точки
            points_item = gl.GLScatterPlotItem(
                pos=points,
                size=size,
                color=color,
                pxMode=True
            )

            # Добавляем в сцену
            self.view.addItem(points_item)

            # Сохраняем ссылку на объект
            if not hasattr(self, 'view_items'):
                self.view_items = {}
            self.view_items[name] = points_item

            # Добавляем в общий словарь items
            self.items[name] = {
                'item': points_item,
                'type': 'points',
                'visible': True
            }

            self.logger.debug(f"Добавлены точки '{name}'")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении точек '{name}': {e}")
            return False

    def add_line(self, name, points, width=1, color=(0.7, 0.7, 0.7, 1.0)):
        """Добавляет линию в сцену"""
        try:
            # Создаем линию
            line_item = gl.GLLinePlotItem(
                pos=points,
                width=width,
                color=color,
                mode='line_strip'
            )

            # Добавляем в сцену
            self.view.addItem(line_item)

            # Сохраняем ссылку на объект
            if not hasattr(self, 'view_items'):
                self.view_items = {}
            self.view_items[name] = line_item

            # Добавляем в общий словарь items
            self.items[name] = {
                'item': line_item,
                'type': 'line',
                'visible': True
            }

            self.logger.debug(f"Добавлена линия '{name}'")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении линии '{name}': {e}")
            return False

    def view_mouse_press_event(self, event):
        """Обработчик нажатия мыши для GLViewWidget"""
        # Сохраняем начальную позицию для определения перетаскивания
        self.mouse_press_pos = event.position().toPoint()
        self.is_dragging = False

        # Сохраняем позицию для обработки вращения/перемещения камеры
        self.last_pos = event.position().toPoint()

        # Проверяем, находимся ли мы в режиме перетаскивания объекта (Shift + ЛКМ)
        # и есть ли выбранный объект
        if event.modifiers() == Qt.ShiftModifier and event.button() == Qt.LeftButton and self.selected_object:
            self.start_object_drag(event)
        else:
            # Стандартный режим
            self.mousePressed.emit(event.position().x(), event.position().y())
            # Вызываем оригинальный обработчик GLViewWidget
            gl.GLViewWidget.mousePressEvent(self.view, event)

    def view_mouse_release_event(self, event):
        """Обработчик отпускания мыши для GLViewWidget"""
        # Проверяем, были ли мы в режиме перетаскивания объекта
        if self.drag_object_mode:
            self.end_object_drag()
        # Если это был клик (а не перетаскивание)
        elif not self.is_dragging and self.mouse_press_pos is not None:
            # Проверяем, что мышь не сдвинулась слишком далеко (порог перетаскивания)
            delta = event.position().toPoint() - self.mouse_press_pos
            if delta.manhattanLength() <= self.drag_threshold:
                # Проверяем режим взаимодействия (только левый клик без модификаторов)
                if event.button() == Qt.LeftButton and not event.modifiers():
                    # Получаем координаты клика
                    mouse_x = event.position().x()
                    mouse_y = event.position().y()

                    # Нормализованные координаты клика
                    nx = (2.0 * mouse_x) / self.view.width() - 1.0
                    ny = 1.0 - (2.0 * mouse_y) / self.view.height()

                    # Делегируем поиск объекта в отдельную функцию
                    self.handle_object_pick(nx, ny)

        # Сбрасываем состояние
        self.mouse_press_pos = None
        self.is_dragging = False

        # Вызываем оригинальный обработчик, если не в режиме перетаскивания объекта
        if not self.drag_object_mode:
            gl.GLViewWidget.mouseReleaseEvent(self.view, event)

        # Сигнал отпускания
        self.mouseReleased.emit(event.position().x(), event.position().y())

    def view_mouse_move_event(self, event):
        """Обработчик движения мыши для GLViewWidget"""
        if self.last_pos is None:
            self.last_pos = event.position().toPoint()
            return

        dx = event.position().x() - self.last_pos.x()
        dy = event.position().y() - self.last_pos.y()

        # Если мышь сдвинулась больше порога, считаем что это перетаскивание
        if self.mouse_press_pos is not None:
            delta = event.position().toPoint() - self.mouse_press_pos
            if delta.manhattanLength() > self.drag_threshold:
                self.is_dragging = True

        # Если находимся в режиме перетаскивания объекта
        if self.drag_object_mode:
            self.drag_object(event)

        else:
            # Стандартное управление камерой - используем оригинальный обработчик
            gl.GLViewWidget.mouseMoveEvent(self.view, event)

        self.last_pos = event.position().toPoint()

    def start_object_drag(self, event):
        """Начинает режим перетаскивания объекта"""
        if not self.selected_object or self.selected_object not in self.view_items:
            return

        self.drag_object_mode = True
        self.drag_start_pos = event.position().toPoint()

        # Получаем текущие координаты объекта
        item = self.view_items[self.selected_object]
        transform = item.transform().matrix()
        position = np.array([transform[0, 3], transform[1, 3], transform[2, 3]])
        self.drag_object_initial_pos = position

        # Создаем плоскость перетаскивания, перпендикулярную направлению взгляда
        camera_pos = np.array(self.view.cameraPosition())
        view_vector = camera_pos - position
        self.drag_plane_normal = view_vector / np.linalg.norm(view_vector)
        self.drag_plane_point = position

        self.logger.debug(f"Начато перетаскивание объекта {self.selected_object}")

    def end_object_drag(self):
        """Завершает режим перетаскивания объекта"""
        self.drag_object_mode = False
        self.drag_start_pos = None
        self.drag_plane_normal = None
        self.drag_plane_point = None
        self.drag_object_initial_pos = None
        self.logger.debug(f"Завершено перетаскивание объекта {self.selected_object}")

    def drag_object(self, event):
        """Обрабатывает перетаскивание объекта"""
        if not self.selected_object or not self.drag_object_mode:
            return

        # Получаем луч из текущей позиции мыши
        mouse_x = event.position().x()
        mouse_y = event.position().y()
        nx = (2.0 * mouse_x) / self.view.width() - 1.0
        ny = 1.0 - (2.0 * mouse_y) / self.view.height()

        ray_origin, ray_direction = self.screen_point_to_ray(nx, ny)

        # Находим пересечение луча с плоскостью
        t = self.ray_plane_intersection(ray_origin, ray_direction,
                                        self.drag_plane_point, self.drag_plane_normal)

        if t is not None:
            # Вычисляем новую позицию
            intersection_point = ray_origin + ray_direction * t

            # Обновляем только положение объекта, сохраняя текущие rotation и scale
            self.set_transform(self.selected_object, position=intersection_point)

            # Отправляем сигнал о трансформации
            self.object_transformed.emit(self.selected_object, intersection_point.tolist())

    def ray_plane_intersection(self, ray_origin, ray_direction, plane_point, plane_normal):
        """
        Вычисляет пересечение луча с плоскостью
        
        Args:
            ray_origin: Начало луча
            ray_direction: Направление луча
            plane_point: Точка на плоскости
            plane_normal: Нормаль плоскости
        
        Returns:
            float или None: Параметр t для пересечения или None, если пересечения нет
        """
        # Проверяем, что луч не параллелен плоскости
        denom = np.dot(ray_direction, plane_normal)
        if abs(denom) < 1e-6:
            return None

        # Вычисляем t
        t = np.dot(plane_point - ray_origin, plane_normal) / denom

        # Проверяем, что пересечение впереди начала луча
        if t < 0:
            return None

        return t

    def mouseMoveEvent(self, event):
        """Обработка движения мыши"""
        if event.buttons() & Qt.LeftButton:
            delta = event.position().toPoint() - self.mouse_press_pos
            mouse_x = event.position().x()
            mouse_y = event.position().y()

            # Обновляем положение камеры
            self.update_camera(delta, mouse_x, mouse_y)
            self.last_pos = event.position().toPoint()

    def wheelEvent(self, event):
        """Обработка колеса мыши"""
        delta = event.angleDelta().y() / 120.0
        self.view.opts['distance'] *= 0.9 ** delta
        self.view.update()
        self.update_lods()  # Обновляем LOD

    def ray_intersect(self, ray_origin, ray_direction, transform):
        """
        Проверяет пересечение луча с объектом и возвращает точку пересечения
        
        Args:
            ray_origin: Начало луча (x, y, z)
            ray_direction: Направление луча (x, y, z)
            transform: Матрица трансформации объекта
            
        Returns:
            tuple: (distance, intersection_point) или (None, None)
        """
        try:
            # Получаем матрицу трансформации
            model_data = transform.data()
            model_matrix = np.array([model_data[i:i + 4] for i in range(0, 16, 4)])

            # Получаем обратную матрицу трансформации
            inv_model = np.linalg.inv(model_matrix)

            # Преобразуем луч в локальное пространство объекта
            local_origin = inv_model @ np.append(ray_origin, 1.0)
            local_origin = local_origin[:3] / local_origin[3]

            local_direction = inv_model @ np.append(ray_direction, 0.0)
            local_direction = local_direction[:3]
            local_direction = local_direction / np.linalg.norm(local_direction)

            # Сначала проверяем пересечение с ограничивающим боксом для оптимизации
            invdir = np.divide(1.0, local_direction,
                               where=local_direction != 0,
                               out=np.full_like(local_direction, np.inf))

            t1 = (-1 - local_origin) * invdir
            t2 = (1 - local_origin) * invdir

            t_min = np.min([t1, t2], axis=0)
            t_max = np.max([t1, t2], axis=0)

            t_enter = np.max(t_min)
            t_exit = np.min(t_max)

            if t_enter <= t_exit and t_exit >= 0:
                # Если объект - это меш, проверяем пересечение с треугольниками
                if hasattr(transform, 'opts') and 'meshdata' in transform.opts:
                    mesh_data = transform.opts['meshdata']
                    vertices = mesh_data.vertexes()
                    faces = mesh_data.faces()

                    min_distance = float('inf')
                    closest_point = None

                    # Проверяем каждый треугольник
                    for face in faces:
                        v0, v1, v2 = vertices[face]

                        # Вычисляем пересечение луча с треугольником (алгоритм Möller–Trumbore)
                        edge1 = v1 - v0
                        edge2 = v2 - v0
                        h = np.cross(local_direction, edge2)
                        a = np.dot(edge1, h)

                        if abs(a) < 1e-6:  # Луч параллелен треугольнику
                            continue

                        f = 1.0 / a
                        s = local_origin - v0
                        u = f * np.dot(s, h)

                        if u < 0.0 or u > 1.0:
                            continue

                        q = np.cross(s, edge1)
                        v = f * np.dot(local_direction, q)

                        if v < 0.0 or u + v > 1.0:
                            continue

                        t = f * np.dot(edge2, q)

                        if t > 1e-6:  # Пересечение найдено
                            if t < min_distance:
                                min_distance = t
                                closest_point = local_origin + local_direction * t

                    if closest_point is not None:
                        # Преобразуем точку обратно в мировое пространство
                        world_point = model_matrix @ np.append(closest_point, 1.0)
                        world_point = world_point[:3] / world_point[3]

                        # Вычисляем реальное расстояние в мировом пространстве
                        distance = np.linalg.norm(world_point - ray_origin)

                        return distance, world_point

                else:  # Для не-мешей используем пересечение с боксом
                    t = t_enter if t_enter > 0 else t_exit
                    local_point = local_origin + local_direction * t

                    # Преобразуем точку обратно в мировое пространство
                    world_point = model_matrix @ np.append(local_point, 1.0)
                    world_point = world_point[:3] / world_point[3]

                    # Вычисляем реальное расстояние в мировом пространстве
                    distance = np.linalg.norm(world_point - ray_origin)

                    return distance, world_point

            return None, None

        except Exception as e:
            print(f"Ошибка при проверке пересечения: {e}")
            return None, None

    def screen_point_to_ray(self, x: float, y: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Преобразует нормализованные координаты экрана в луч в мировом пространстве
        
        Args:
            x: нормализованная координата X экрана (-1 до 1)
            y: нормализованная координата Y экрана (-1 до 1)
        
        Returns:
            Tuple[np.ndarray, np.ndarray]: начало луча (позиция камеры) и направление луча
        """
        # Получаем матрицы с учетом column-major порядка
        view_matrix = np.array(self.view.viewMatrix().data()).reshape(4, 4).T
        proj_matrix = np.array(self.view.projectionMatrix().data()).reshape(4, 4).T

        # Вычисляем обратную матрицу (вид + проекция)
        inv_proj_view = np.linalg.inv(proj_matrix @ view_matrix)

        # Точка в NDC пространстве (z=-1 для ближней плоскости)
        point_ndc = np.array([x, y, -1.0, 1.0])

        # Преобразуем в мировые координаты
        world_point = inv_proj_view @ point_ndc
        world_point /= world_point[3]

        # Направление луча
        ray_origin = np.array(self.view.cameraPosition())
        ray_direction = world_point[:3] - ray_origin
        ray_direction /= np.linalg.norm(ray_direction)

        return ray_origin, ray_direction

    def handle_object_pick(self, nx, ny):
        """Обработка выбора объекта по нормализованным координатам экрана"""
        try:
            # Получаем луч из точки клика
            ray_origin, ray_direction = self.screen_point_to_ray(nx, ny)

            candidates = []
            min_distance = float('inf')

            # Проверяем пересечение луча с каждым объектом
            for name, item in self.view_items.items():
                # Пропускаем служебные объекты и невидимые
                if name in ['grid', 'axes'] or not item.visible():
                    continue

                # Проверяем пересечение
                intersection = self.check_ray_intersection(ray_origin, ray_direction, item)

                if intersection is not None:
                    distance = np.linalg.norm(intersection - ray_origin)
                    self.logger.debug(f"Найдено пересечение с {name}: расстояние={distance:.3f}")

                    candidates.append({
                        'name': name,
                        'distance': distance,
                        'intersection': intersection
                    })

            if candidates:
                # Сортируем по расстоянию
                candidates.sort(key=lambda x: x['distance'])
                selected = candidates[0]['name']

                # Проверяем, не выбран ли уже этот объект
                if selected != self.selected_object:
                    self.logger.info(f"Выбран объект: {selected}")
                    # Подсвечиваем выбранный объект
                    self.highlight_object(selected)
                    self.object_selected.emit(selected)
            else:
                # Если объект не найден, снимаем выделение с текущего
                if self.selected_object:
                    self.highlight_object(self.selected_object, False)
                    self.selected_object = None
                self.logger.debug("Объект не найден")

        except Exception as e:
            self.logger.error(f"Ошибка при выборе объекта: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

    def check_ray_intersection(self, ray_origin, ray_direction, item):
        """
        Проверяет пересечение луча с объектом
        
        Args:
            ray_origin: начало луча
            ray_direction: направление луча
            item: объект для проверки пересечения
        
        Returns:
            np.ndarray или None: точка пересечения или None, если пересечения нет
        """
        try:
            # Получаем матрицу трансформации объекта
            transform = item.transform()

            # Создаем обратную матрицу для перевода луча в пространство объекта
            try:
                model_data = transform.matrix().data()
                model_matrix = np.array(model_data).reshape(4, 4)
            except TypeError:
                # Если data не является callable, то пробуем как атрибут
                model_matrix = np.array(transform.matrix().data).reshape(4, 4)

            # Получаем обратную матрицу трансформации
            inv_model = np.linalg.inv(model_matrix)

            # Преобразуем луч в локальное пространство объекта
            local_origin = inv_model @ np.append(ray_origin, 1.0)
            local_origin = local_origin[:3] / local_origin[3]

            local_direction = inv_model @ np.append(ray_direction, 0.0)
            local_direction = local_direction[:3]
            local_direction = local_direction / np.linalg.norm(local_direction)

            # Проверяем пересечение с ограничивающим боксом (-1 до 1 в локальном пространстве)
            invdir = np.divide(1.0, local_direction,
                               where=local_direction != 0,
                               out=np.full_like(local_direction, np.inf))

            t1 = (-1 - local_origin) * invdir
            t2 = (1 - local_origin) * invdir

            t_min = np.min([t1, t2], axis=0)
            t_max = np.max([t1, t2], axis=0)

            t_enter = np.max(t_min)
            t_exit = np.min(t_max)

            if t_enter <= t_exit and t_exit >= 0:
                # Если объект - это меш, и есть meshdata, проверяем пересечение с треугольниками
                if hasattr(item, 'opts') and 'meshdata' in item.opts:
                    mesh_data = item.opts['meshdata']
                    vertices = mesh_data.vertexes()
                    faces = mesh_data.faces()

                    min_distance = float('inf')
                    closest_point = None

                    # Проверяем каждый треугольник
                    for face in faces:
                        if len(face) < 3:
                            continue

                        v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]

                        # Алгоритм Möller–Trumbore для пересечения луча с треугольником
                        edge1 = v1 - v0
                        edge2 = v2 - v0
                        h = np.cross(local_direction, edge2)
                        a = np.dot(edge1, h)

                        if abs(a) < 1e-6:  # Луч параллелен треугольнику
                            continue

                        f = 1.0 / a
                        s = local_origin - v0
                        u = f * np.dot(s, h)

                        if u < 0.0 or u > 1.0:
                            continue

                        q = np.cross(s, edge1)
                        v = f * np.dot(local_direction, q)

                        if v < 0.0 or u + v > 1.0:
                            continue

                        t = f * np.dot(edge2, q)

                        if t > 1e-6 and t < min_distance:  # Пересечение найдено
                            min_distance = t
                            closest_point = local_origin + local_direction * t

                    if closest_point is not None:
                        # Преобразуем точку обратно в мировое пространство
                        world_point = model_matrix @ np.append(closest_point, 1.0)
                        world_point = world_point[:3] / world_point[3]
                        return world_point

                else:  # Для не-мешей используем пересечение с боксом
                    t = t_enter if t_enter > 0 else t_exit
                    local_point = local_origin + local_direction * t

                    # Преобразуем точку обратно в мировое пространство
                    world_point = model_matrix @ np.append(local_point, 1.0)
                    world_point = world_point[:3] / world_point[3]
                    return world_point

            return None

        except Exception as e:
            self.logger.error(f"Ошибка при проверке пересечения: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def debug_draw_ray(self, start, end):
        """
        Рисует луч для отладки

        Args:
            start: начальная точка луча
            end: конечная точка луча
        """
        # Удаляем предыдущий луч, если он существует
        if hasattr(self, 'debug_ray') and self.debug_ray in self.view.items:
            self.view.removeItem(self.debug_ray)

        # Создаем новый луч
        ray_points = np.array([start, end])
        self.debug_ray = gl.GLLinePlotItem(pos=ray_points, color=(1, 0, 0, 1), width=2)
        self.view.addItem(self.debug_ray)

        print(f"DEBUG: Добавлен луч от {start} до {end}")

    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши"""
        if event.button() == Qt.LeftButton:
            self.mouseReleased.emit(event.position().x(), event.position().y())

    def set_transform(self, name: str, position=None, rotation=None, scale=None):
        """Устанавливает трансформацию объекта"""
        if name in self.view_items:
            try:
                item = self.view_items[name]

                # Если передана только позиция, обновляем только её
                if position is not None and rotation is None and scale is None:
                    current_transform = item.transform()
                    # Извлекаем текущую позицию из матрицы трансформации
                    current_position = np.array([
                        current_transform[0, 3],
                        current_transform[1, 3],
                        current_transform[2, 3]
                    ])

                    # Вычисляем разницу позиций
                    delta_position = np.array(position) - current_position
                    # Применяем только смещение
                    item.translate(*delta_position)

                # Если нужно обновить все трансформации
                else:
                    item.resetTransform()  # Сбрасываем только если меняем всё

                    # Применяем трансформации в правильном порядке
                    # Сначала масштаб
                    if scale is not None:
                        item.scale(*scale)
                    else:
                        item.scale(1, 1, 1)  # Устанавливаем единичный масштаб

                    # Затем вращение (если задано)
                    if rotation is not None:
                        rx, ry, rz = rotation
                        # Преобразуем в градусы, если значения малы
                        if abs(rx) < 6.28 and abs(ry) < 6.28 and abs(rz) < 6.28:
                            rx = rx * 180 / 3.14159
                            ry = ry * 180 / 3.14159
                            rz = rz * 180 / 3.14159

                        # Применяем вращения
                        item.rotate(rx, 1, 0, 0)  # Вокруг X
                        item.rotate(ry, 0, 1, 0)  # Вокруг Y
                        item.rotate(rz, 0, 0, 1)  # Вокруг Z

                    # В конце перемещение
                    if position is not None:
                        item.translate(*position)

                # Принудительно обновляем вид
                self.view.update()
                return True

            except Exception as e:
                print(f"[VIEWPORT] Ошибка при установке трансформации для '{name}': {e}")
                return False
        return False

    def highlight_object(self, name: str, highlight: bool = True):
        """
        Подсвечивает выбранный объект
        """
        if name in self.view_items:
            item = self.view_items[name]

            if highlight:
                # Если выделяем новый объект
                if self.selected_object and self.selected_object != name:
                    # Сначала снимаем подсветку с предыдущего
                    self.highlight_object(self.selected_object, False)

                # Сохраняем оригинальный цвет
                if name not in self.original_colors:
                    self.original_colors[name] = item._current_color

                # Делаем цвет ярче
                current_color = item._current_color
                highlight_color = tuple(min(1.0, c * 1.3) for c in current_color[:3]) + (current_color[3],)
                item.setColor(highlight_color)
                item._current_color = highlight_color

                self.selected_object = name
            else:
                # Возвращаем оригинальный цвет
                if name in self.original_colors:
                    original_color = self.original_colors[name]
                    item.setColor(original_color)
                    item._current_color = original_color
                    del self.original_colors[name]

                if self.selected_object == name:
                    self.selected_object = None

            self.view.update()

    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши"""
        if event.button() == Qt.LeftButton:
            self.mouse_press_pos = event.position().toPoint()
            self.last_pos = event.position().toPoint()
            self.mousePressed.emit(event.position().x(), event.position().y())

    def mouseMoveEvent(self, event):
        """Обработка движения мыши"""
        if event.buttons() & Qt.LeftButton:
            delta = event.position().toPoint() - self.mouse_press_pos
            mouse_x = event.position().x()
            mouse_y = event.position().y()

            # Обновляем положение камеры
            self.update_camera(delta, mouse_x, mouse_y)
            self.last_pos = event.position().toPoint()

    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши"""
        if event.button() == Qt.LeftButton:
            self.mouseReleased.emit(event.position().x(), event.position().y())

    def paintGL(self):
        """Отрисовка OpenGL"""
        current_time = time.time()
        dt = current_time - self._last_frame_time

        # Пропускаем кадр если:
        # 1. Сцена не изменилась
        # 2. Прошло слишком мало времени с последнего кадра
        # 3. Не происходит вращение камеры
        if (not self._scene_changed and
                dt < self._min_frame_time and
                not self._rotating):
            return

        # Обычная отрисовка
        self.gl_view.paintGL()

        # Сбрасываем флаг изменений и обновляем время
        self._scene_changed = False
        self._last_frame_time = current_time

    def set_debug_colliders(self, enabled: bool):
        """Включает или выключает отображение коллайдеров"""
        self.debug_colliders = enabled
        self._update_collider_visibility()

    def _update_collider_visibility(self):
        """Обновляет видимость всех коллайдеров"""
        for collider_items in self.collider_visualizations.values():
            for item in collider_items:
                item.setVisible(self.debug_colliders)
        self.view.update()

    def _create_sphere_lines(self, center, radius, phi_segments=12, theta_segments=6):
        """Создает все точки для линий сферы за один проход"""
        phi = np.linspace(0, 2 * np.pi, phi_segments)
        theta = np.linspace(-np.pi / 2, np.pi / 2, theta_segments)

        # Создаем все точки сразу
        points = []

        # Горизонтальные круги (по theta)
        for t in theta:
            circle_points = []
            for p in phi:
                x = center[0] + radius * np.cos(t) * np.cos(p)
                y = center[1] + radius * np.cos(t) * np.sin(p)
                z = center[2] + radius * np.sin(t)
                circle_points.append([x, y, z])
            # Замыкаем круг
            circle_points.append(circle_points[0])
            points.extend(circle_points)

        # Вертикальные линии (по phi)
        for p in phi:
            line_points = []
            for t in theta:
                x = center[0] + radius * np.cos(t) * np.cos(p)
                y = center[1] + radius * np.cos(t) * np.sin(p)
                z = center[2] + radius * np.sin(t)
                line_points.append([x, y, z])
            points.extend(line_points)

        return np.array(points)

    def update_collider(self, name: str, collider_data: Optional[dict]):
        """Обновляет визуализацию коллайдера для объекта"""
        # Если данные коллайдера None или физика выключена, просто очищаем визуализацию
        if collider_data is None or not self.debug_colliders:
            if name in self.collider_visualizations:
                for item in self.collider_visualizations[name]:
                    item.setVisible(False)
            return

        if collider_data['type'] == 'sphere':
            # Создаем или переиспользуем одну линию для всей сферы
            if name not in self.collider_visualizations:
                line = gl.GLLinePlotItem(color=(1, 0, 0, 1), width=1)
                self.view.addItem(line)
                self.collider_visualizations[name] = [line]
            else:
                line = self.collider_visualizations[name][0]

            # Обновляем все точки сразу
            points = self._create_sphere_lines(
                collider_data.get('center', (0, 0, 0)),
                collider_data['radius']
            )
            line.setData(pos=points)
            line.setVisible(True)

        elif collider_data['type'] == 'box':
            bounds = collider_data['data']['bounds']
            vertices = []

            # Создаем вершины куба
            for x in [bounds[0], bounds[3]]:
                for y in [bounds[1], bounds[4]]:
                    for z in [bounds[2], bounds[5]]:
                        vertices.append([x, y, z])

            edges = [
                (0, 1), (1, 3), (3, 2), (2, 0),  # Нижняя грань
                (4, 5), (5, 7), (7, 6), (6, 4),  # Верхняя грань
                (0, 4), (1, 5), (2, 6), (3, 7)  # Вертикальные ребра
            ]

            # Создаем или переиспользуем одну линию для всего куба
            if name not in self.collider_visualizations:
                line = gl.GLLinePlotItem(color=(1, 0, 0, 1), width=1)
                self.view.addItem(line)
                self.collider_visualizations[name] = [line]
            else:
                line = self.collider_visualizations[name][0]

            # Создаем все точки для куба
            points = []
            for start, end in edges:
                points.extend([vertices[start], vertices[end]])

            # Обновляем все точки сразу
            line.setData(pos=np.array(points))
            line.setVisible(True)
