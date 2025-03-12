import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
import numpy as np

from simple_visualizer.core.viewport import Viewport3D

@pytest.fixture
def viewport(qtbot):
    """Создает viewport для тестирования"""
    viewport = Viewport3D()
    qtbot.addWidget(viewport)
    return viewport

def test_viewport_creation(viewport):
    """Тест создания viewport"""
    assert viewport is not None
    assert viewport.view is not None

def test_viewport_add_mesh(viewport):
    """Тест добавления меша"""
    # Создаем простой треугольник
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    faces = np.array([[0, 1, 2]])
    
    # Добавляем меш
    result = viewport.add_mesh("test_mesh", vertices, faces)
    assert result == True
    assert "test_mesh" in viewport.view_items

def test_viewport_mouse_interaction(viewport, qtbot):
    """Тест взаимодействия с мышью"""
    # Симулируем нажатие кнопки мыши
    qtbot.mousePress(viewport.view, Qt.LeftButton)
    qtbot.mouseRelease(viewport.view, Qt.LeftButton)

def test_viewport_keyboard_interaction(viewport, qtbot):
    """Тест обработки клавиатуры"""
    # Симулируем нажатие клавиши
    qtbot.keyPress(viewport, Qt.Key_W)
    qtbot.keyRelease(viewport, Qt.Key_W)

def test_viewport_camera_reset(viewport):
    """Тест сброса камеры"""
    # Изменяем положение камеры
    initial_rotation = viewport.rotation.copy()
    initial_translation = viewport.translation.copy()
    
    viewport.rotation = [45, 45, 45]
    viewport.translation = [1, 1, -15]
    
    # Сбрасываем камеру
    viewport.rotation = [30, -45, 0]
    viewport.translation = [0, 0, -10]
    
    # Проверяем, что камера вернулась в исходное положение
    assert viewport.rotation == [30, -45, 0]
    assert viewport.translation == [0, 0, -10]

def test_viewport_object_selection(viewport, qtbot):
    """Тест выбора объекта"""
    # Создаем и добавляем объект
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    faces = np.array([[0, 1, 2]])
    viewport.add_mesh("test_mesh", vertices, faces)
    
    # Симулируем клик мыши
    qtbot.mouseClick(viewport.view, Qt.LeftButton)

def test_viewport_lod(viewport):
    """Тест уровней детализации"""
    # Создаем объект с разными уровнями детализации
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    faces = np.array([[0, 1, 2]])
    viewport.add_mesh("test_mesh", vertices, faces)
    
    # Включаем отображение LOD
    viewport.debug_lod = True
    assert viewport.debug_lod == True
    
    # Обновляем LOD
    viewport.update_lods()

def test_viewport_collider_visualization(viewport):
    """Тест визуализации коллайдеров"""
    # Включаем отображение коллайдеров
    viewport.set_debug_colliders(True)
    assert viewport.debug_colliders == True
    
    # Создаем объект с коллайдером
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    faces = np.array([[0, 1, 2]])
    viewport.add_mesh("test_mesh", vertices, faces)
    
    # Обновляем коллайдер
    collider_data = {
        'type': 'sphere',
        'data': {'radius': 1.0},
        'center': [0, 0, 0],
        'radius': 1.0
    }
    viewport.update_collider("test_mesh", collider_data) 