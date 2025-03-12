import logging
import math
import time
from math import sin, cos
import numpy as np
from typing import Dict, Any, Optional, Tuple, Callable
from PySide6.QtCore import QObject, Signal

from ..animation_thread import AnimationThread
from ..object3d import Object3D


class AnimationManager(QObject):
    """Менеджер анимаций объектов"""

    animation_state_changed = Signal(str, bool)  # name, is_running
    animation_error_occurred = Signal(str, str)  # name, error_message
    object_updated = Signal(str, dict)  # name, data

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("simple_visualizer.core.managers.animation_manager")
        self.animation_threads = {}
        self.animation_scripts = {}

    def set_object_script(self, name: str, obj: Object3D, move_script: str, rotation_script: str) -> bool:
        """Устанавливает скрипты анимации для объекта"""
        try:
            # Компилируем скрипты для проверки синтаксиса
            if move_script:
                compile(move_script, '<string>', 'exec')
            if rotation_script:
                compile(rotation_script, '<string>', 'exec')

            # Сохраняем скрипты
            self.animation_scripts[name] = {
                'move_script': move_script,
                'rotation_script': rotation_script
            }

            # Обновляем скрипты в объекте
            obj.set_animation_scripts(move_script, rotation_script)
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при установке скриптов анимации для {name}: {e}")
            self.animation_error_occurred.emit(name, str(e))
            return False

    def run_animation(self, name: str, obj: Object3D) -> bool:
        """Запускает анимацию объекта"""
        if name in self.animation_threads and self.animation_threads[name].running:
            self.logger.warning(f"Анимация для {name} уже запущена")
            return False

        if name not in self.animation_scripts:
            self.logger.error(f"Нет скриптов анимации для {name}")
            return False

        scripts = self.animation_scripts[name]
        
        # Создаем глобальные переменные для скрипта
        globals_dict = {
            'sin': sin,
            'cos': cos,
            'pi': math.pi,
            'math': math,
            'np': np,
            'radians': math.radians,
            'degrees': math.degrees,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'atan2': math.atan2,
            'sqrt': math.sqrt,
            'pow': math.pow
        }

        # Создаем и запускаем поток анимации
        animation_thread = AnimationThread(
            obj,
            scripts['move_script'],
            scripts['rotation_script'],
            globals_dict
        )

        # Подключаем сигналы
        animation_thread.error_occurred.connect(
            lambda error: self._handle_animation_error(name, error))
        animation_thread.transform_updated.connect(
            lambda transform_data: self._handle_transform_updated(name, obj, transform_data))
        animation_thread.object_updated.connect(
            lambda: self._handle_object_updated(name, obj))

        self.animation_threads[name] = animation_thread
        animation_thread.start()

        self.animation_state_changed.emit(name, True)
        self.logger.info(f"Анимация запущена для {name}")
        return True

    def stop_animation(self, name: str) -> bool:
        """Останавливает анимацию объекта"""
        if name not in self.animation_threads:
            return False

        thread = self.animation_threads[name]
        if thread.running:
            thread.stop()
            thread.wait()
            self.animation_state_changed.emit(name, False)
            self.logger.info(f"Анимация остановлена для {name}")

        return True

    def stop_all_animations(self) -> None:
        """Останавливает все анимации"""
        for name in list(self.animation_threads.keys()):
            self.stop_animation(name)

    def is_animation_running(self, name: str) -> bool:
        """Проверяет, запущена ли анимация для объекта"""
        return name in self.animation_threads and self.animation_threads[name].running

    def _handle_animation_error(self, name: str, error: str):
        """Обрабатывает ошибки анимации"""
        self.logger.error(f"Ошибка анимации для {name}: {error}")
        self.animation_error_occurred.emit(name, error)
        self.stop_animation(name)

    def _handle_transform_updated(self, name: str, obj: Object3D, transform_data: dict):
        """Обрабатывает обновление трансформации из потока анимации"""
        # Отправляем сигнал об обновлении
        self.object_updated.emit(name, transform_data)

    def _handle_object_updated(self, name: str, obj: Object3D):
        """Обрабатывает обновление объекта"""
        transform_data = {
            'position': obj.position,
            'rotation': obj.rotation,
            'scale': obj.scale
        }
        self.object_updated.emit(name, transform_data)