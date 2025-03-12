from PySide6.QtCore import QThread, Signal
import time
import math
import numpy as np
from typing import Dict, Any


class AnimationThread(QThread):
    """Поток для анимации объекта"""

    error_occurred = Signal(str)  # Сигнал об ошибке
    object_updated = Signal()  # Сигнал об обновлении объекта
    transform_updated = Signal(dict)  # Сигнал об обновлении трансформации

    def __init__(self, obj, move_script, rotation_script, globals_dict, use_relative=False):
        super().__init__()
        self.obj = obj
        self.move_script = move_script
        self.rotation_script = rotation_script
        self.globals_dict = globals_dict
        self.use_relative = use_relative
        self.running = False
        self.start_time = None

        # Добавляем ссылку на объект в globals
        self.globals_dict['self'] = self.obj
        self.globals_dict['obj'] = self.obj
        self.globals_dict['position'] = self.obj.position
        self.globals_dict['rotation'] = self.obj.rotation
        # Добавляем t для совместимости с существующими скриптами
        self.globals_dict['t'] = time.time()

        # Сохраняем начальные позиции
        self.initial_position = self.obj.position
        self.initial_rotation = self.obj.rotation

    def run(self):
        """Запускает анимацию"""
        self.running = True
        self.start_time = time.time()
        last_update = self.start_time

        while self.running:
            try:
                current_time = time.time()
                t = current_time - self.start_time
                dt = current_time - last_update
                last_update = current_time

                # Обновляем t в globals
                self.globals_dict['t'] = t
                self.globals_dict['dt'] = dt

                transform_data = {}

                # Выполняем скрипт движения
                if self.move_script:
                    local_vars = {'t': t, 'dt': dt, 'result': None}
                    self.globals_dict['x'] = self.obj.position[0]
                    self.globals_dict['y'] = self.obj.position[1]
                    self.globals_dict['z'] = self.obj.position[2]
                    exec(self.move_script, self.globals_dict, local_vars)
                    if 'result' in local_vars and local_vars['result']:
                        new_position = local_vars['result']
                        transform_data['position'] = new_position

                # Выполняем скрипт вращения
                if self.rotation_script:
                    local_vars = {'t': t, 'dt': dt, 'result': None}
                    # Добавляем углы поворота
                    self.globals_dict['rx'] = self.obj.rotation[0]
                    self.globals_dict['ry'] = self.obj.rotation[1]
                    self.globals_dict['rz'] = self.obj.rotation[2]
                    exec(self.rotation_script, self.globals_dict, local_vars)
                    if 'result' in local_vars and local_vars['result']:
                        new_rotation = local_vars['result']
                        transform_data['rotation'] = new_rotation

                # Применяем трансформацию к объекту
                if transform_data:
                    self.obj.set_transform(
                        position=transform_data.get('position'),
                        rotation=transform_data.get('rotation')
                    )
                    # Отправляем сигнал с обновленными данными
                    self.transform_updated.emit(transform_data)
                    self.object_updated.emit()

                time.sleep(0.016)  # ~60 FPS

            except Exception as e:
                self.error_occurred.emit(str(e))
                self.running = False
                break

    def stop(self):
        """Останавливает анимацию"""
        self.running = False
