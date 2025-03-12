import pytest
import numpy as np
from simple_visualizer.core.simple_shapes import (
    create_cube, create_sphere, create_torus,
    create_cone, create_cylinder, create_floor
)

class TestSimpleShapes:
    def test_create_cube(self):
        """Тест создания куба"""
        size = 2.0
        vertices, faces = create_cube(size=size)
        
        # Проверяем, что все вершины находятся на расстоянии size/2 от центра
        max_coords = np.max(np.abs(vertices), axis=1)
        assert np.allclose(max_coords, size/2)
        
        # Проверяем количество вершин и граней
        assert len(vertices) == 8  # куб имеет 8 вершин
        assert len(faces) == 12    # куб имеет 12 треугольников (6 граней по 2 треугольника)

    def test_create_sphere(self):
        """Тест создания сферы"""
        radius = 1.5
        resolution = 10
        vertices, faces = create_sphere(radius=radius, resolution=resolution)
        
        # Проверяем, что все вершины находятся на расстоянии radius от центра
        distances = np.linalg.norm(vertices, axis=1)
        assert np.allclose(distances, radius, rtol=1e-2)
        
        # Проверяем, что количество вершин и граней соответствует resolution
        expected_vertices = resolution * resolution
        assert len(vertices) == expected_vertices

    def test_create_torus(self):
        """Тест создания тора"""
        major_radius = 2.0
        minor_radius = 0.5
        resolution = 10
        vertices, faces = create_torus(major_radius=major_radius, minor_radius=minor_radius, resolution=resolution)
        
        # Проверяем, что все точки находятся на правильном расстоянии от центра тора
        # Для тора это сложнее, так как точки находятся на поверхности кольца
        xy_distances = np.sqrt(vertices[:, 0]**2 + vertices[:, 1]**2)
        assert np.allclose(xy_distances, major_radius, rtol=0.5)

    def test_create_cone(self):
        """Тест создания конуса"""
        radius = 1.5
        height = 3.0
        resolution = 10
        vertices, faces = create_cone(radius=radius, height=height, resolution=resolution)
        
        # Проверяем вершину конуса
        assert any(np.allclose(v, [0, 0, height/2]) for v in vertices)
        
        # Проверяем основание
        base_vertices = vertices[np.abs(vertices[:, 2] + height/2) < 1e-6]
        base_distances = np.sqrt(base_vertices[:, 0]**2 + base_vertices[:, 1]**2)
        # Исключаем центральную точку основания из проверки
        outer_points = base_distances > 0
        assert np.allclose(base_distances[outer_points], radius)

    def test_create_cylinder(self):
        """Тест создания цилиндра"""
        radius = 1.5
        height = 3.0
        resolution = 10
        vertices, faces = create_cylinder(radius=radius, height=height, resolution=resolution)
        
        # Проверяем верхнее и нижнее основания
        top_vertices = vertices[np.abs(vertices[:, 2] - height/2) < 1e-6]
        bottom_vertices = vertices[np.abs(vertices[:, 2] + height/2) < 1e-6]
        
        # Проверяем радиус оснований
        top_distances = np.sqrt(top_vertices[:, 0]**2 + top_vertices[:, 1]**2)
        bottom_distances = np.sqrt(bottom_vertices[:, 0]**2 + bottom_vertices[:, 1]**2)
        
        assert np.allclose(top_distances[:-1], radius)  # Исключаем центр основания
        assert np.allclose(bottom_distances[:-1], radius)  # Исключаем центр основания

    def test_create_floor(self):
        """Тест создания пола"""
        size = 50.0
        y = -10.0
        vertices, faces = create_floor(size=size, y=y)
        
        # Проверяем, что пол лежит на заданной высоте
        y_coords = vertices[:, 2]  # Y-координаты всех вершин
        assert np.allclose(y_coords, y)
        
        # Проверяем размеры пола
        x_coords = vertices[:, 0]
        z_coords = vertices[:, 1]
        assert np.min(x_coords) == -size
        assert np.max(x_coords) == size
        assert np.min(z_coords) == -size
        assert np.max(z_coords) == size 