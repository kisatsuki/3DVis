import numpy as np
import logging
from typing import Tuple, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger("simple_visualizer.core.simple_shapes")

class CollisionType(ABC):
    NONE = 0
    SPHERE = 1
    BOX = 2
    CYLINDER = 3
    CONE = 4
    TORUS = 5

class Object3D(ABC):
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.position = np.array([0, 0, 0])
        self.scale = np.array([1, 1, 1])

    @property
    def collision_type(self):
        return self._collision_type

    @abstractmethod
    def get_collision_data(self) -> Dict:
        pass

    def ray_intersect(self, ray_origin, ray_direction):
        if self.collision_type == CollisionType.SPHERE:
            return self._ray_sphere_intersect(ray_origin, ray_direction)
        elif self.collision_type == CollisionType.BOX:
            return self._ray_box_intersect(ray_origin, ray_direction)
        return None

    def _ray_sphere_intersect(self, ray_origin, ray_direction):
        center = np.array(self.position)
        radius = self._collision_data.get('radius', 0.5)
        
        oc = ray_origin - center
        a = np.dot(ray_direction, ray_direction)
        b = 2.0 * np.dot(oc, ray_direction)
        c = np.dot(oc, oc) - radius * radius
        
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None
            
        t = (-b - np.sqrt(discriminant)) / (2.0 * a)
        return t if t > 0 else None

    def _ray_box_intersect(self, ray_origin, ray_direction):
        bounds = self._collision_data.get('bounds', (-0.5, -0.5, -0.5, 0.5, 0.5, 0.5))
        min_bound = np.array(bounds[:3]) + np.array(self.position)
        max_bound = np.array(bounds[3:]) + np.array(self.position)
        
        tx1 = (min_bound[0] - ray_origin[0]) / ray_direction[0]
        tx2 = (max_bound[0] - ray_origin[0]) / ray_direction[0]
        ty1 = (min_bound[1] - ray_origin[1]) / ray_direction[1]
        ty2 = (max_bound[1] - ray_origin[1]) / ray_direction[1]
        tz1 = (min_bound[2] - ray_origin[2]) / ray_direction[2]
        tz2 = (max_bound[2] - ray_origin[2]) / ray_direction[2]
        
        tmin = max(min(tx1, tx2), min(ty1, ty2), min(tz1, tz2))
        tmax = min(max(tx1, tx2), max(ty1, ty2), max(tz1, tz2))
        
        return tmin if tmin <= tmax and tmax > 0 else None

def create_cube(size=1.0, center=(0, 0, 0)):
    """
    Создает куб
    
    Args:
        size: Размер куба
        center: Центр куба (x, y, z)
        
    Returns:
        tuple: (vertices, faces)
    """
    logger.debug(f"Создание куба размером {size} с центром {center}")
    size = size / 2.0
    
    # Вершины
    vertices = np.array([
        [center[0] - size, center[1] - size, center[2] - size],  # 0
        [center[0] + size, center[1] - size, center[2] - size],  # 1
        [center[0] + size, center[1] + size, center[2] - size],  # 2
        [center[0] - size, center[1] + size, center[2] - size],  # 3
        [center[0] - size, center[1] - size, center[2] + size],  # 4
        [center[0] + size, center[1] - size, center[2] + size],  # 5
        [center[0] + size, center[1] + size, center[2] + size],  # 6
        [center[0] - size, center[1] + size, center[2] + size]   # 7
    ])
    
    # Грани (индексы вершин)
    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # нижняя грань
        [4, 5, 6], [4, 6, 7],  # верхняя грань
        [0, 1, 5], [0, 5, 4],  # передняя грань
        [2, 3, 7], [2, 7, 6],  # задняя грань
        [0, 3, 7], [0, 7, 4],  # левая грань
        [1, 2, 6], [1, 6, 5]   # правая грань
    ])
    
    return vertices, faces

def create_sphere(radius=1.0, center=(0, 0, 0), resolution=10):
    """
    Создает сферу
    
    Args:
        radius: Радиус сферы
        center: Центр сферы (x, y, z)
        resolution: Разрешение (количество сегментов)
        
    Returns:
        tuple: (vertices, faces)
    """
    logger.debug(f"Создание сферы радиусом {radius} с центром {center}")
    
    # Создаем сетку углов
    phi = np.linspace(0, np.pi, resolution)
    theta = np.linspace(0, 2*np.pi, resolution)
    phi_grid, theta_grid = np.meshgrid(phi, theta)
    
    # Преобразуем в декартовы координаты
    x = center[0] + radius * np.sin(phi_grid) * np.cos(theta_grid)
    y = center[1] + radius * np.sin(phi_grid) * np.sin(theta_grid)
    z = center[2] + radius * np.cos(phi_grid)
    
    # Формируем массив вершин
    vertices = np.vstack([x.flatten(), y.flatten(), z.flatten()]).T
    
    # Создаем индексы граней
    faces = []
    for i in range(resolution-1):
        for j in range(resolution-1):
            p1 = i * resolution + j
            p2 = i * resolution + (j + 1)
            p3 = (i + 1) * resolution + j
            p4 = (i + 1) * resolution + (j + 1)
            
            faces.append([p1, p2, p4])
            faces.append([p1, p4, p3])
    
    return vertices, np.array(faces)

def create_cylinder(radius=1.0, height=2.0, center=(0, 0, 0), resolution=20):
    """
    Создает цилиндр
    
    Args:
        radius: Радиус цилиндра
        height: Высота цилиндра
        center: Центр цилиндра (x, y, z)
        resolution: Разрешение (количество сегментов)
        
    Returns:
        tuple: (vertices, faces)
    """
    logger.debug(f"Создание цилиндра радиусом {radius}, высотой {height} с центром {center}")
    
    # Создаем верхнее и нижнее основание
    theta = np.linspace(0, 2*np.pi, resolution)
    
    # Верхнее и нижнее основание
    top = np.array([[center[0] + radius * np.cos(t),
                     center[1] + radius * np.sin(t),
                     center[2] + height/2] for t in theta])
                    
    bottom = np.array([[center[0] + radius * np.cos(t),
                        center[1] + radius * np.sin(t),
                        center[2] - height/2] for t in theta])
    
    # Добавляем центры оснований
    top_center = np.array([[center[0], center[1], center[2] + height/2]])
    bottom_center = np.array([[center[0], center[1], center[2] - height/2]])
    
    # Объединяем все вершины
    vertices = np.vstack([top, bottom, top_center, bottom_center])
    
    # Создаем грани боковой поверхности
    faces = []
    for i in range(resolution-1):
        faces.append([i, i+1, i+resolution+1])
        faces.append([i, i+resolution+1, i+resolution])
    
    # Добавляем соединение между последней и первой вершиной
    faces.append([resolution-1, 0, resolution])
    faces.append([resolution-1, resolution, 2*resolution-1])
    
    # Добавляем грани верхнего основания
    for i in range(resolution-1):
        faces.append([i, i+1, 2*resolution])
    faces.append([resolution-1, 0, 2*resolution])
    
    # Добавляем грани нижнего основания
    for i in range(resolution-1):
        faces.append([i+resolution, 2*resolution+1, i+resolution+1])
    faces.append([2*resolution-1, 2*resolution+1, resolution])
    
    return vertices, np.array(faces)

def create_torus(major_radius=1.0, minor_radius=0.3, center=(0, 0, 0), resolution=20):
    """
    Создает тор
    
    Args:
        major_radius: Большой радиус тора
        minor_radius: Малый радиус тора
        center: Центр тора (x, y, z)
        resolution: Разрешение (количество сегментов)
        
    Returns:
        tuple: (vertices, faces)
    """
    logger.debug(f"Создание тора с радиусами {major_radius}/{minor_radius} с центром {center}")
    
    # Создаем сетку углов
    u = np.linspace(0, 2*np.pi, resolution)
    v = np.linspace(0, 2*np.pi, resolution)
    u_grid, v_grid = np.meshgrid(u, v)
    
    # Преобразуем в декартовы координаты
    x = center[0] + (major_radius + minor_radius * np.cos(v_grid)) * np.cos(u_grid)
    y = center[1] + (major_radius + minor_radius * np.cos(v_grid)) * np.sin(u_grid)
    z = center[2] + minor_radius * np.sin(v_grid)
    
    # Формируем массив вершин
    vertices = np.vstack([x.flatten(), y.flatten(), z.flatten()]).T
    
    # Создаем индексы граней
    faces = []
    for i in range(resolution-1):
        for j in range(resolution-1):
            p1 = i * resolution + j
            p2 = i * resolution + (j + 1)
            p3 = (i + 1) * resolution + j
            p4 = (i + 1) * resolution + (j + 1)
            
            faces.append([p1, p2, p4])
            faces.append([p1, p4, p3])
    
    # Соединяем края тора
    for i in range(resolution-1):
        p1 = i * resolution + (resolution-1)
        p2 = i * resolution + 0
        p3 = (i + 1) * resolution + (resolution-1)
        p4 = (i + 1) * resolution + 0
        
        faces.append([p1, p2, p4])
        faces.append([p1, p4, p3])
    
    # Соединяем верхний и нижний края
    for j in range(resolution-1):
        p1 = (resolution-1) * resolution + j
        p2 = (resolution-1) * resolution + (j + 1)
        p3 = 0 * resolution + j
        p4 = 0 * resolution + (j + 1)
        
        faces.append([p1, p2, p4])
        faces.append([p1, p4, p3])
    
    return vertices, np.array(faces)

def create_cone(radius=1.0, height=2.0, center=(0, 0, 0), resolution=20):
    """
    Создает конус
    
    Args:
        radius: Радиус основания конуса
        height: Высота конуса
        center: Центр конуса (x, y, z)
        resolution: Разрешение (количество сегментов)
        
    Returns:
        tuple: (vertices, faces)
    """
    logger.debug(f"Создание конуса радиусом {radius}, высотой {height} с центром {center}")
    
    # Создаем основание
    theta = np.linspace(0, 2*np.pi, resolution)
    base = np.array([[center[0] + radius * np.cos(t),
                      center[1] + radius * np.sin(t),
                      center[2] - height/2] for t in theta])
    
    # Вершина конуса и центр основания
    apex = np.array([[center[0], center[1], center[2] + height/2]])
    base_center = np.array([[center[0], center[1], center[2] - height/2]])
    
    # Объединяем все вершины
    vertices = np.vstack([base, apex, base_center])
    
    # Создаем грани боковой поверхности
    faces = []
    for i in range(resolution-1):
        faces.append([i, i+1, resolution])
    faces.append([resolution-1, 0, resolution])
    
    # Добавляем грани основания
    for i in range(resolution-1):
        faces.append([i, resolution+1, i+1])
    faces.append([resolution-1, resolution+1, 0])
    
    return vertices, np.array(faces)

def create_floor(size: float = 50.0, y: float = -10.0) -> Tuple[np.ndarray, np.ndarray]:
    """Создает вершины и грани для пола
    
    Args:
        size: размер пола (половина стороны квадрата)
        y: высота пола
    
    Returns:
        vertices: вершины пола
        faces: грани пола
    """
    vertices = np.array([
        [-size, -size, y],  # Большой прямоугольник
        [size, -size, y],
        [size, size, y],
        [-size, size, y]
    ])
    
    faces = np.array([
        [0, 1, 2],  # Две треугольные грани
        [0, 2, 3]
    ])
    
    return vertices, faces

class Sphere3D(Object3D):
    def __init__(self, name: str, radius: float = 1.0, **kwargs):
        super().__init__(name, **kwargs)
        self._collision_type = CollisionType.SPHERE
        self._collision_data = {
            'radius': radius
        }

    def get_collision_data(self) -> Dict:
        return {
            'type': CollisionType.SPHERE,
            'radius': self._collision_data['radius'] * max(self.scale),
            'center': self.position
        }

class Box3D(Object3D):
    def __init__(self, name: str, size: Tuple[float, float, float] = (1.0, 1.0, 1.0), **kwargs):
        super().__init__(name, **kwargs)
        self._collision_type = CollisionType.BOX
        half_size = tuple(s/2 for s in size)
        self._collision_data = {
            'bounds': (-half_size[0], -half_size[1], -half_size[2],
                      half_size[0], half_size[1], half_size[2])
        }

    def get_collision_data(self) -> Dict:
        return {
            'type': 'box',
            'data': {
                'bounds': self._calculate_scaled_bounds(),
                'size': self.calculate_bounding_radius() * 2
            }
        }
        
    def _calculate_scaled_bounds(self):
        """Рассчитывает границы с учетом масштаба"""
        bounds = self._collision_data['bounds']
        scale = self.scale
        min_bound = [bounds[i] * scale[i % 3] for i in range(3)]
        max_bound = [bounds[i+3] * scale[i % 3] for i in range(3)]
        return (*min_bound, *max_bound)

    def calculate_bounding_radius(self):
        bounds = self._collision_data['bounds']
        scale = self.scale
        return max(abs(b * s) for b, s in zip(bounds[:3], scale))

    def ray_intersect(self, ray_origin, ray_direction):
        if self.collision_type == CollisionType.BOX:
            return self._ray_box_intersect(ray_origin, ray_direction)
        return None

    def _ray_box_intersect(self, ray_origin, ray_direction):
        bounds = self._collision_data['bounds']
        min_bound = np.array(bounds[:3]) + np.array(self.position)
        max_bound = np.array(bounds[3:]) + np.array(self.position)
        
        tx1 = (min_bound[0] - ray_origin[0]) / ray_direction[0]
        tx2 = (max_bound[0] - ray_origin[0]) / ray_direction[0]
        ty1 = (min_bound[1] - ray_origin[1]) / ray_direction[1]
        ty2 = (max_bound[1] - ray_origin[1]) / ray_direction[1]
        tz1 = (min_bound[2] - ray_origin[2]) / ray_direction[2]
        tz2 = (max_bound[2] - ray_origin[2]) / ray_direction[2]
        
        tmin = max(min(tx1, tx2), min(ty1, ty2), min(tz1, tz2))
        tmax = min(max(tx1, tx2), max(ty1, ty2), max(tz1, tz2))
        
        return tmin if tmin <= tmax and tmax > 0 else None

class Cylinder3D(Object3D):
    def __init__(self, name: str, radius: float = 1.0, height: float = 2.0, **kwargs):
        super().__init__(name, **kwargs)
        self._collision_type = CollisionType.CYLINDER
        self._collision_data = {
            'radius': radius,
            'height': height
        }
    
    def get_collision_data(self) -> Dict:
        """Получает данные о коллайдере цилиндра"""
        scaled_radius = self._collision_data['radius'] * max(self.scale[0], self.scale[1])
        scaled_height = self._collision_data['height'] * self.scale[2]
        
        return {
            'type': CollisionType.CYLINDER,
            'data': {
                'radius': scaled_radius,
                'height': scaled_height
            },
            'center': self.position,
            'radius': scaled_radius,
            'height': scaled_height
        }

    def ray_intersect(self, ray_origin, ray_direction):
        """Проверка пересечения луча с цилиндром"""
        if self.collision_type != CollisionType.CYLINDER:
            return None
            
        radius = self._collision_data['radius'] * max(self.scale[0], self.scale[1])
        height = self._collision_data['height'] * self.scale[2]
        half_height = height / 2.0
        
        # Вектор от начала луча до центра цилиндра
        oc = ray_origin - self.position
        
        # Проверяем пересечение с боковой поверхностью цилиндра
        # (игнорируем координату Z)
        a = ray_direction[0]**2 + ray_direction[1]**2
        b = 2.0 * (oc[0] * ray_direction[0] + oc[1] * ray_direction[1])
        c = oc[0]**2 + oc[1]**2 - radius**2
        
        discriminant = b**2 - 4 * a * c
        
        if discriminant < 0:
            return None
            
        t1 = (-b - np.sqrt(discriminant)) / (2.0 * a)
        t2 = (-b + np.sqrt(discriminant)) / (2.0 * a)
        
        # Берем ближайшее положительное пересечение
        t = t1 if t1 > 0 else t2
        
        if t <= 0:
            return None
            
        # Проверяем, находится ли точка пересечения в пределах высоты цилиндра
        hit_point = ray_origin + ray_direction * t
        hit_height = hit_point[2] - self.position[2]
        
        if abs(hit_height) <= half_height:
            return t
            
        # Проверяем пересечение с верхним и нижним основаниями
        t_top = (self.position[2] + half_height - ray_origin[2]) / ray_direction[2]
        t_bottom = (self.position[2] - half_height - ray_origin[2]) / ray_direction[2]
        
        # Проверяем верхнее основание
        if t_top > 0:
            hit_point = ray_origin + ray_direction * t_top
            dx = hit_point[0] - self.position[0]
            dy = hit_point[1] - self.position[1]
            if dx**2 + dy**2 <= radius**2:
                return t_top
                
        # Проверяем нижнее основание
        if t_bottom > 0:
            hit_point = ray_origin + ray_direction * t_bottom
            dx = hit_point[0] - self.position[0]
            dy = hit_point[1] - self.position[1]
            if dx**2 + dy**2 <= radius**2:
                return t_bottom
                
        return None

class Cone3D(Object3D):
    def __init__(self, name: str, radius: float = 1.0, height: float = 2.0, **kwargs):
        super().__init__(name, **kwargs)
        self._collision_type = CollisionType.CONE
        self._collision_data = {
            'radius': radius,
            'height': height
        }
    
    def get_collision_data(self) -> Dict:
        """Получает данные о коллайдере конуса"""
        scaled_radius = self._collision_data['radius'] * max(self.scale[0], self.scale[1])
        scaled_height = self._collision_data['height'] * self.scale[2]
        
        return {
            'type': CollisionType.CONE,
            'data': {
                'radius': scaled_radius,
                'height': scaled_height
            },
            'center': self.position,
            'radius': scaled_radius,
            'height': scaled_height
        }
        
    def ray_intersect(self, ray_origin, ray_direction):
        """Проверка пересечения луча с конусом"""
        if self.collision_type != CollisionType.CONE:
            return None
            
        radius = self._collision_data['radius'] * max(self.scale[0], self.scale[1])
        height = self._collision_data['height'] * self.scale[2]
        
        # Вектор от начала луча до центра конуса
        oc = ray_origin - self.position
        
        # Вершина конуса находится на высоте height/2 от центра
        apex = self.position + np.array([0, 0, height/2])
        # Центр основания находится на высоте -height/2 от центра
        base_center = self.position + np.array([0, 0, -height/2])
        
        # Вектор направления оси конуса (от основания к вершине)
        axis = np.array([0, 0, 1])
        
        # Угол раствора конуса
        half_angle = np.arctan(radius / height)
        cos_half_angle = np.cos(half_angle)
        
        # Проверка пересечения с боковой поверхностью конуса
        co = ray_origin - apex
        cos_angle = np.dot(co, axis) / np.linalg.norm(co)
        
        # Если луч проходит через вершину конуса
        if np.linalg.norm(co) < 1e-6:
            return 0.0
            
        # Проверяем пересечение с боковой поверхностью
        a = ray_direction[0]**2 + ray_direction[1]**2 - ray_direction[2]**2 * (radius / height)**2
        b = 2.0 * (co[0] * ray_direction[0] + co[1] * ray_direction[1] - 
                  co[2] * ray_direction[2] * (radius / height)**2)
        c = co[0]**2 + co[1]**2 - co[2]**2 * (radius / height)**2
        
        discriminant = b**2 - 4 * a * c
        
        if abs(a) < 1e-6:
            if abs(b) < 1e-6:
                return None
            t = -c / b
            if t > 0:
                hit_point = ray_origin + ray_direction * t
                # Проверяем, что точка находится внутри конуса
                if hit_point[2] >= apex[2]:
                    return None
                if hit_point[2] <= base_center[2]:
                    return None
                return t
            return None
            
        if discriminant < 0:
            return None
            
        t1 = (-b - np.sqrt(discriminant)) / (2.0 * a)
        t2 = (-b + np.sqrt(discriminant)) / (2.0 * a)
        
        # Берем ближайшее положительное пересечение
        t = t1 if t1 > 0 else t2
        
        if t <= 0:
            return None
            
        # Проверяем, находится ли точка пересечения в пределах конуса
        hit_point = ray_origin + ray_direction * t
        if hit_point[2] > apex[2] or hit_point[2] < base_center[2]:
            return None
            
        return t
        
class Torus3D(Object3D):
    def __init__(self, name: str, major_radius: float = 1.0, minor_radius: float = 0.3, **kwargs):
        super().__init__(name, **kwargs)
        self._collision_type = CollisionType.TORUS
        self._collision_data = {
            'major_radius': major_radius,
            'minor_radius': minor_radius
        }
    
    def get_collision_data(self) -> Dict:
        """Получает данные о коллайдере тора"""
        scaled_major = self._collision_data['major_radius'] * max(self.scale[0], self.scale[1])
        scaled_minor = self._collision_data['minor_radius'] * self.scale[2]
        
        return {
            'type': CollisionType.TORUS,
            'data': {
                'major_radius': scaled_major,
                'minor_radius': scaled_minor
            },
            'center': self.position,
            'major_radius': scaled_major,
            'minor_radius': scaled_minor
        }
        
    def ray_intersect(self, ray_origin, ray_direction):
        """Проверка пересечения луча с тором (аппроксимация)"""
        if self.collision_type != CollisionType.TORUS:
            return None
            
        # Для тора сложно найти точное аналитическое решение
        # Используем приближение на основе сферы
        
        major_radius = self._collision_data['major_radius'] * max(self.scale[0], self.scale[1])
        minor_radius = self._collision_data['minor_radius'] * self.scale[2]
        
        # Вектор от начала луча до центра тора
        oc = ray_origin - self.position
        
        # Проецируем на плоскость XY
        oc_xy = np.array([oc[0], oc[1], 0])
        length_xy = np.linalg.norm(oc_xy)
        
        if length_xy < 1e-6:
            # Луч проходит через центр тора, используем приближение
            sphere_radius = major_radius + minor_radius
            
            a = np.dot(ray_direction, ray_direction)
            b = 2.0 * np.dot(oc, ray_direction)
            c = np.dot(oc, oc) - sphere_radius**2
            
            discriminant = b**2 - 4 * a * c
            
            if discriminant < 0:
                return None
                
            t = (-b - np.sqrt(discriminant)) / (2.0 * a)
            return t if t > 0 else None
        
        # Найдем ближайшую точку на кольце тора
        normalized_oc_xy = oc_xy / length_xy
        ring_point = normalized_oc_xy * major_radius
        
        # Создадим сферу в этой точке радиусом minor_radius
        sphere_center = self.position + ring_point
        
        # Проверяем пересечение со сферой
        oc_sphere = ray_origin - sphere_center
        
        a = np.dot(ray_direction, ray_direction)
        b = 2.0 * np.dot(oc_sphere, ray_direction)
        c = np.dot(oc_sphere, oc_sphere) - minor_radius**2
        
        discriminant = b**2 - 4 * a * c
        
        if discriminant < 0:
            return None
            
        t = (-b - np.sqrt(discriminant)) / (2.0 * a)
        return t if t > 0 else None 

def create_box_object(name: str, size: float = 1.0, position: Tuple[float, float, float] = (0, 0, 0)):
    """
    Создает объект куба с соответствующим коллайдером
    
    Args:
        name: Имя объекта
        size: Размер куба (или tuple для разных размеров по осям)
        position: Позиция объекта (x, y, z)
        
    Returns:
        Box3D: Объект куба с коллайдером
    """
    # Преобразуем size в tuple, если передано одно значение
    if isinstance(size, (int, float)):
        size = (size, size, size)
    
    # Создаем объект куба
    cube = Box3D(name, size=size)
    cube.position = np.array(position)
    
    return cube

def create_sphere_object(name: str, radius: float = 1.0, position: Tuple[float, float, float] = (0, 0, 0)):
    """
    Создает объект сферы с соответствующим коллайдером
    
    Args:
        name: Имя объекта
        radius: Радиус сферы
        position: Позиция объекта (x, y, z)
        
    Returns:
        Sphere3D: Объект сферы с коллайдером
    """
    # Создаем объект сферы
    sphere = Sphere3D(name, radius=radius)
    sphere.position = np.array(position)
    
    return sphere

def create_cylinder_object(name: str, radius: float = 1.0, height: float = 2.0, 
                         position: Tuple[float, float, float] = (0, 0, 0)):
    """
    Создает объект цилиндра с соответствующим коллайдером
    
    Args:
        name: Имя объекта
        radius: Радиус цилиндра
        height: Высота цилиндра
        position: Позиция объекта (x, y, z)
        
    Returns:
        Cylinder3D: Объект цилиндра с коллайдером
    """
    # Создаем объект цилиндра
    cylinder = Cylinder3D(name, radius=radius, height=height)
    cylinder.position = np.array(position)
    
    return cylinder

def create_cone_object(name: str, radius: float = 1.0, height: float = 2.0, 
                     position: Tuple[float, float, float] = (0, 0, 0)):
    """
    Создает объект конуса с соответствующим коллайдером
    
    Args:
        name: Имя объекта
        radius: Радиус основания конуса
        height: Высота конуса
        position: Позиция объекта (x, y, z)
        
    Returns:
        Cone3D: Объект конуса с коллайдером
    """
    # Создаем объект конуса
    cone = Cone3D(name, radius=radius, height=height)
    cone.position = np.array(position)
    
    return cone

def create_torus_object(name: str, major_radius: float = 1.0, minor_radius: float = 0.3, 
                      position: Tuple[float, float, float] = (0, 0, 0)):
    """
    Создает объект тора с соответствующим коллайдером
    
    Args:
        name: Имя объекта
        major_radius: Большой радиус тора
        minor_radius: Малый радиус тора
        position: Позиция объекта (x, y, z)
        
    Returns:
        Torus3D: Объект тора с коллайдером
    """
    # Создаем объект тора
    torus = Torus3D(name, major_radius=major_radius, minor_radius=minor_radius)
    torus.position = np.array(position)
    
    return torus 