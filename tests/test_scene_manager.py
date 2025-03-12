import pytest
import numpy as np
from simple_visualizer.core.scene_manager import SceneManager

class TestSceneManager:
    @pytest.fixture
    def scene_manager(self):
        return SceneManager()

    def test_add_mesh(self, scene_manager):
        """Тест добавления меша в сцену"""
        # Создаем простой треугольник
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        
        # Добавляем меш
        result = scene_manager.add_mesh("test_mesh", vertices, faces)
        assert result == True
        assert "test_mesh" in scene_manager.objects

    def test_remove_object(self, scene_manager):
        """Тест удаления объекта из сцены"""
        # Сначала добавляем объект
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        scene_manager.add_mesh("test_mesh", vertices, faces)
        
        # Удаляем объект
        result = scene_manager.remove_object("test_mesh")
        assert result == True
        assert "test_mesh" not in scene_manager.objects

    def test_clear_scene(self, scene_manager):
        """Тест очистки сцены"""
        # Добавляем несколько объектов
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        
        scene_manager.add_mesh("mesh1", vertices, faces)
        scene_manager.add_mesh("mesh2", vertices, faces)
        
        # Очищаем сцену
        scene_manager.clear()
        assert len(scene_manager.objects) == 0

    def test_object_visibility(self, scene_manager):
        """Тест изменения видимости объекта"""
        # Добавляем объект
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        scene_manager.add_mesh("test_mesh", vertices, faces)
        
        # Изменяем видимость
        result = scene_manager.set_visibility("test_mesh", False)
        assert result == True
        
        # Проверяем состояние объекта
        obj_data = scene_manager.get_object_data("test_mesh")
        assert obj_data['visible'] == False 