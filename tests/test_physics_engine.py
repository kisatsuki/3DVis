import pytest
import numpy as np
from simple_visualizer.core.physics_engine import PhysicsEngine
from simple_visualizer.core.object3d import Mesh3D

class TestPhysicsEngine:
    @pytest.fixture
    def physics_engine(self):
        return PhysicsEngine()

    @pytest.fixture
    def test_object(self):
        # Создаем простой тестовый объект
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        obj = Mesh3D("test_object", vertices, faces)
        return obj

    def test_register_object(self, physics_engine, test_object):
        """Тест регистрации объекта в физическом движке"""
        physics_engine.register_object(test_object)
        assert test_object.name in physics_engine.objects
        assert test_object.name in physics_engine.physics_params

    def test_unregister_object(self, physics_engine, test_object):
        """Тест удаления объекта из физического движка"""
        physics_engine.register_object(test_object)
        physics_engine.unregister_object(test_object.name)
        assert test_object.name not in physics_engine.objects
        assert test_object.name not in physics_engine.physics_params

    def test_physics_params(self, physics_engine, test_object):
        """Тест установки и получения физических параметров"""
        params = {
            'mass': 2.0,
            'velocity': [1, 0, 0],
            'is_static': True
        }
        physics_engine.register_object(test_object, params)
        
        # Проверяем, что параметры установлены корректно
        obj_params = physics_engine.get_physics_params(test_object.name)
        assert obj_params['mass'] == 2.0
        assert obj_params['velocity'] == [1, 0, 0]
        assert obj_params['is_static'] == True

    def test_gravity(self, physics_engine):
        """Тест установки гравитации"""
        new_gravity = (0, -5, 0)
        physics_engine.set_gravity(new_gravity)
        assert physics_engine.gravity == new_gravity 