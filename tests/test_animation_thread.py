import pytest
from unittest.mock import MagicMock, patch
import time
from simple_visualizer.core.animation_thread import AnimationThread
from simple_visualizer.core.object3d import Mesh3D
import numpy as np

class TestAnimationThread:
    @pytest.fixture
    def test_object(self):
        """Создает тестовый объект для анимации"""
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        return Mesh3D("test_object", vertices, faces)

    @pytest.fixture
    def simple_move_script(self):
        """Простой скрипт для движения"""
        return """
result = [x + t, y, z]
"""

    @pytest.fixture
    def simple_rotation_script(self):
        """Простой скрипт для вращения"""
        return """
result = [rx + t * 10, ry, rz]
"""

    def test_animation_thread_creation(self, test_object, simple_move_script, simple_rotation_script):
        """Тест создания потока анимации"""
        thread = AnimationThread(test_object, simple_move_script, simple_rotation_script, {})
        assert thread.obj == test_object
        assert thread.running == False
        assert thread.move_script == simple_move_script
        assert thread.rotation_script == simple_rotation_script

    def test_animation_thread_start_stop(self, test_object, simple_move_script, qtbot):
        """Тест запуска и остановки анимации"""
        thread = AnimationThread(test_object, simple_move_script, None, {})
        
        # Подключаем сигнал обновления объекта
        update_signal = MagicMock()
        thread.object_updated.connect(update_signal)
        
        # Запускаем анимацию
        thread.start()
        
        # Ждем обновления
        qtbot.wait(100)
        
        # Останавливаем анимацию
        thread.stop()
        thread.wait()  # Ждем завершения потока
        
        # Проверяем, что сигнал был отправлен
        assert update_signal.called

    def test_animation_movement(self, test_object, simple_move_script, qtbot):
        """Тест движения объекта"""
        thread = AnimationThread(test_object, simple_move_script, None, {})
        
        # Запоминаем начальную позицию
        initial_position = np.array(test_object.position)
        
        # Подключаем сигнал обновления трансформации
        transform_signal = MagicMock()
        thread.transform_updated.connect(transform_signal)
        
        # Запускаем анимацию
        thread.start()
        
        # Ждем обновления
        qtbot.wait(100)
        
        # Останавливаем анимацию
        thread.stop()
        thread.wait()  # Ждем завершения потока
        
        # Проверяем, что позиция изменилась и сигнал был отправлен
        assert not np.array_equal(np.array(test_object.position), initial_position)
        assert transform_signal.called

    def test_animation_rotation(self, test_object, simple_rotation_script, qtbot):
        """Тест вращения объекта"""
        thread = AnimationThread(test_object, None, simple_rotation_script, {})
        
        # Запоминаем начальный поворот
        initial_rotation = np.array(test_object.rotation)
        
        # Подключаем сигнал обновления трансформации
        transform_signal = MagicMock()
        thread.transform_updated.connect(transform_signal)
        
        # Запускаем анимацию
        thread.start()
        
        # Ждем обновления
        qtbot.wait(100)
        
        # Останавливаем анимацию
        thread.stop()
        thread.wait()  # Ждем завершения потока
        
        # Проверяем, что поворот изменился и сигнал был отправлен
        assert not np.array_equal(np.array(test_object.rotation), initial_rotation)
        assert transform_signal.called

    def test_animation_error_handling(self, test_object, qtbot):
        """Тест обработки ошибок в скрипте"""
        # Устанавливаем скрипт с ошибкой
        error_script = "result = undefined_variable"
        thread = AnimationThread(test_object, error_script, None, {})
        
        # Подключаем обработчик сигнала ошибки
        error_handler = MagicMock()
        thread.error_occurred.connect(error_handler)
        
        # Запускаем анимацию
        thread.start()
        
        # Ждем обработки ошибки
        qtbot.wait(100)
        
        # Останавливаем анимацию
        thread.stop()
        thread.wait()  # Ждем завершения потока
        
        # Проверяем, что ошибка была обработана
        assert error_handler.called

    def test_script_globals(self, test_object, qtbot):
        """Тест доступности глобальных переменных в скрипте"""
        # Скрипт, использующий математические функции
        math_script = """
import math
result = [math.sin(t), math.cos(t), 0]
"""
        thread = AnimationThread(test_object, math_script, None, {'math': __import__('math')})
        
        # Подключаем сигнал обновления трансформации
        transform_signal = MagicMock()
        thread.transform_updated.connect(transform_signal)
        
        # Запускаем анимацию
        thread.start()
        
        # Ждем обновления
        qtbot.wait(100)
        
        # Останавливаем анимацию
        thread.stop()
        thread.wait()  # Ждем завершения потока
        
        # Проверяем, что позиция изменилась и сигнал был отправлен
        assert any(abs(x) > 0 for x in test_object.position)
        assert transform_signal.called 