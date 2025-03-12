import numpy as np
import logging
from typing import Tuple, Dict
from abc import ABC, abstractmethod

logger = logging.getLogger("simple_visualizer.core.simple_shapes")

class CollisionType(ABC):
    NONE = 0
    SPHERE = 1
    BOX = 2
    CYLINDER = 3

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
                'size': self.calculate_bounding_radius() * 2
            }
        }

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