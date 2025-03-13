import logging
import numpy as np
from typing import Dict, Any, Optional
import time
from PySide6.QtCore import QObject, Signal

from simple_visualizer.core.object3d import Mesh3D


class PhysicsEngine(QObject):
    """Физический движок для 3D объектов"""
    
    # Сигнал для обновления визуализации коллайдера
    collider_updated = Signal(str, dict)  # (object_name, collider_data)
    # Сигнал для обновления позиции объекта в вьюпорте
    object_position_updated = Signal(str, tuple)  # (object_name, position)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("simple_visualizer.core.physics_engine")
        self.objects = {}  # Словарь объектов с включенной физикой
        self.physics_params = {}  # Словарь физических параметров для каждого объекта
        self.last_update = time.time()
        self.gravity = (0, 0, -9.81)  # Гравитация по умолчанию
        self.damping = 0.98  # Коэффициент затухания
        self.velocity_threshold = 0.01  # Пороговое значение скорости для остановки

    def register_object(self, obj: Any, params: Optional[Dict] = None) -> None:
        """
        Регистрирует объект в физическом движке
        
        Args:
            obj: Объект для регистрации
            params: Физические параметры (если None, используются параметры по умолчанию)
        """
        # Получаем размер объекта для коллайдера по умолчанию
        bounding_radius = obj.calculate_bounding_radius() if hasattr(obj, 'calculate_bounding_radius') else 1.0
        bounds = obj.update_bounds() if hasattr(obj, 'update_bounds') else (-1, -1, -1, 1, 1, 1)

        default_params = {
            'enabled': True,
            'mass': 1.0,
            'velocity': [0, 0, 0],
            'acceleration': list(self.gravity),
            'is_static': False,
            'restitution': 0.5,
            'friction': 0.3,
            'collider_type': 'sphere',  # По умолчанию используем сферический коллайдер
            'collider_data': {
                'radius': bounding_radius,  # Для сферы
                'bounds': bounds,  # Для куба
                'height': bounding_radius * 2,  # Для цилиндра
                'radius_cylinder': bounding_radius * 0.5  # Для цилиндра
            },
            'bounds': bounds
        }

        # Определяем тип коллайдера на основе геометрии объекта
        if hasattr(obj, 'get_collision_data'):
            collision_data = obj.get_collision_data()
            collider_type = collision_data.get('type', 'sphere')
            collider_data = collision_data.get('data', default_params['collider_data'])
            
            default_params['collider_type'] = collider_type
            # Обновляем только существующие данные, сохраняя значения по умолчанию
            default_params['collider_data'].update(collider_data or {})

        # Обновляем параметры из переданного словаря
        if params:
            # Особая обработка для collider_data, чтобы не потерять значения по умолчанию
            if 'collider_data' in params:
                default_params['collider_data'].update(params.pop('collider_data'))
            default_params.update(params)

        self.objects[obj.name] = obj
        self.physics_params[obj.name] = default_params
        self.logger.debug(
            f"Объект '{obj.name}' зарегистрирован в физическом движке с коллайдером "
            f"типа {default_params['collider_type']}"
        )

        # Эмитим сигнал для обновления визуализации коллайдера
        self._emit_collider_update(obj.name)

    def _emit_collider_update(self, name: str):
        """Отправляет сигнал с данными коллайдера"""
        if name not in self.physics_params:
            return

        params = self.physics_params[name]
        
        # Если физика выключена, отправляем сигнал с None для очистки коллайдера
        if not params['enabled']:
            self.collider_updated.emit(name, None)
            return

        collider_data = {
            'type': params['collider_type'],
            'data': params['collider_data'].copy()
        }

        # Получаем дополнительные параметры в зависимости от типа коллайдера
        obj = self.objects[name]
        
        # Получаем коллизионные данные из объекта, если возможно
        if hasattr(obj, 'get_collision_data'):
            obj_collision_data = obj.get_collision_data()
            collider_type = obj_collision_data.get('type', params['collider_type'])
            
            # Обновляем тип коллайдера, если он предоставлен объектом
            collider_data['type'] = collider_type
            
            # Для сферического коллайдера
            if collider_type == 1:  # CollisionType.SPHERE
                collider_data['radius'] = obj_collision_data.get('radius', 1.0)
                collider_data['center'] = obj.position
                
            # Для кубического коллайдера
            elif collider_type == 2:  # CollisionType.BOX
                collider_data['bounds'] = obj_collision_data.get('bounds')
                collider_data['center'] = obj.position
                
            # Для цилиндрического коллайдера
            elif collider_type == 3:  # CollisionType.CYLINDER
                collider_data['radius'] = obj_collision_data.get('radius', 1.0)
                collider_data['height'] = obj_collision_data.get('height', 2.0)
                collider_data['center'] = obj.position
                
            # Для конического коллайдера
            elif collider_type == 4:  # CollisionType.CONE
                collider_data['radius'] = obj_collision_data.get('radius', 1.0)
                collider_data['height'] = obj_collision_data.get('height', 2.0)
                collider_data['center'] = obj.position
                
            # Для тора
            elif collider_type == 5:  # CollisionType.TORUS
                collider_data['major_radius'] = obj_collision_data.get('major_radius', 1.0)
                collider_data['minor_radius'] = obj_collision_data.get('minor_radius', 0.3)
                collider_data['center'] = obj.position
                
        else:
            # Запасной вариант, если объект не предоставляет метод get_collision_data
            collider_type = params['collider_type']
            
            # Для сферического коллайдера
            if collider_type == 'sphere' or collider_type == 1:
                collider_data['radius'] = params['collider_data'].get('radius', 1.0)
                collider_data['center'] = obj.position
                
            # Для кубического коллайдера
            elif collider_type == 'box' or collider_type == 2:
                # Если bounds не задан, используем default
                if 'bounds' not in params['collider_data']:
                    # Устанавливаем bounds по умолчанию
                    size = 1.0
                    half_size = size / 2
                    collider_data['bounds'] = (-half_size, -half_size, -half_size, half_size, half_size, half_size)
                else:
                    collider_data['bounds'] = params['collider_data']['bounds']
                collider_data['center'] = obj.position
                
            # Для цилиндрического коллайдера
            elif collider_type == 'cylinder' or collider_type == 3:
                collider_data['radius'] = params['collider_data'].get('radius', 1.0)
                collider_data['height'] = params['collider_data'].get('height', 2.0)
                collider_data['center'] = obj.position
                
            # Для конического коллайдера
            elif collider_type == 'cone' or collider_type == 4:
                collider_data['radius'] = params['collider_data'].get('radius', 1.0)
                collider_data['height'] = params['collider_data'].get('height', 2.0)
                collider_data['center'] = obj.position
                
            # Для тора
            elif collider_type == 'torus' or collider_type == 5:
                collider_data['major_radius'] = params['collider_data'].get('major_radius', 1.0)
                collider_data['minor_radius'] = params['collider_data'].get('minor_radius', 0.3)
                collider_data['center'] = obj.position

        self.collider_updated.emit(name, collider_data)

    def unregister_object(self, name: str) -> None:
        """Удаляет объект из физического движка"""
        self.objects.pop(name, None)
        self.physics_params.pop(name, None)
        self.logger.debug(f"Объект '{name}' удален из физического движка")

    def is_physics_enabled(self, name: str) -> bool:
        """Проверяет, включена ли физика для объекта"""
        return name in self.physics_params and self.physics_params[name]['enabled']

    def get_physics_params(self, name: str) -> Optional[Dict]:
        """Возвращает физические параметры объекта"""
        return self.physics_params.get(name)

    def set_physics_params(self, name: str, params: Dict) -> None:
        """Устанавливает физические параметры для объекта"""
        if name in self.physics_params:
            self.physics_params[name].update(params)

    def update(self) -> None:
        """Обновляет физическую симуляцию"""
        current_time = time.time()
        dt = min(current_time - self.last_update, 0.1)  # Ограничиваем dt для стабильности
        self.last_update = current_time

        # Обновляем все объекты
        for name, obj in list(self.objects.items()):
            params = self.physics_params[name]
            if not params['enabled']:
                continue

            # Обновляем границы объекта
            params['bounds'] = obj.update_bounds()

            # Если объект не статичный - обновляем его движение
            if not params['is_static']:
                # Обновляем скорость с учетом ускорения и трения
                velocity = list(params['velocity'])
                acceleration = params['acceleration']

                # Вычисляем силу трения
                speed = sum(v*v for v in velocity) ** 0.5
                if speed > 0:
                    friction_force = params['friction'] * 9.81  # μ * g
                    friction_deceleration = friction_force / params['mass']
                    
                    # Применяем трение против направления движения
                    friction_dt = min(dt, speed / friction_deceleration)  # Предотвращаем отрицательную скорость
                    for i in range(3):
                        if abs(velocity[i]) > 0:
                            # Направление силы трения противоположно скорости
                            friction_acceleration = -(velocity[i] / speed) * friction_deceleration
                            velocity[i] += friction_acceleration * friction_dt

                # Применяем основное ускорение
                for i in range(3):
                    velocity[i] += acceleration[i] * dt

                # Проверяем, не слишком ли мала скорость
                speed = sum(v*v for v in velocity) ** 0.5
                if speed < self.velocity_threshold:
                    velocity = [0, 0, 0]

                # Обновляем позицию объекта
                position = list(obj.position)
                for i in range(3):
                    position[i] += velocity[i] * dt

                # Проверяем столкновение с "землей"
                if position[2] < 0:
                    position[2] = 0
                    velocity[2] = -velocity[2] * params['restitution']

                # Применяем новую позицию и скорость
                obj.position = tuple(position)
                params['velocity'] = tuple(velocity)  # Сохраняем обратно как tuple
                
                # Отправляем сигнал об обновлении позиции для визуализации
                self.object_position_updated.emit(name, obj.position)

        # Проверяем столкновения между объектами
        self._check_collisions()

        # Эмитим сигналы для обновления визуализации коллайдеров
        for name in self.objects:
            self._emit_collider_update(name)

    def _check_collisions(self) -> None:
        """Проверяет столкновения между всеми объектами"""
        objects = list(self.objects.values())
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                if self._check_collision(objects[i], objects[j]):
                    self._handle_collision(objects[i], objects[j])

    def _check_collision(self, obj1: Any, obj2: Any) -> bool:
        """Проверяет столкновение между двумя объектами"""
        params1 = self.physics_params[obj1.name]
        params2 = self.physics_params[obj2.name]

        if params1['is_static'] and params2['is_static']:
            return False

        if not (params1['enabled'] and params2['enabled']):
            return False

        # Получаем радиусы из геометрии объектов
        size1 = obj1.calculate_bounding_radius()
        size2 = obj2.calculate_bounding_radius()

        # Вычисляем центры объектов
        pos1 = obj1.position
        pos2 = obj2.position

        # Вычисляем реальное расстояние между центрами
        distance = sum((p1 - p2) ** 2 for p1, p2 in zip(pos1, pos2)) ** 0.5
        
        # Вычисляем глубину проникновения
        penetration = (size1 + size2) - distance
        
        # Игнорируем очень маленькие проникновения (меньше 1% от суммы радиусов)
        min_penetration = (size1 + size2) * 0.01
        if penetration < min_penetration:
            return False

        # Проверяем реальное столкновение
        collision = distance < (size1 + size2)

        if collision:
            self.logger.debug(f"Реальное расстояние: {distance}")
            self.logger.debug(f"Сумма радиусов: {size1 + size2}")
            self.logger.debug(f"Глубина проникновения: {penetration}")
            self.logger.debug(f"Позиция 1: {pos1}")
            self.logger.debug(f"Позиция 2: {pos2}")

        return collision

    def _handle_collision(self, obj1: Mesh3D, obj2: Mesh3D) -> None:
        """Обрабатывает столкновение между двумя объектами"""
        params1 = self.physics_params[obj1.name]
        params2 = self.physics_params[obj2.name]

        # Если оба объекта статичные - пропускаем
        if params1['is_static'] and params2['is_static']:
            return

        # Получаем массы и скорости
        m1 = params1['mass']
        m2 = params2['mass']
        v1 = list(params1['velocity'])
        v2 = list(params2['velocity'])

        # Позиции объектов
        pos1 = list(obj1.position)
        pos2 = list(obj2.position)

        # Вычисляем вектор нормали столкновения (от obj1 к obj2)
        direction = [p2 - p1 for p1, p2 in zip(pos1, pos2)]
        length = sum(d*d for d in direction) ** 0.5
        if length == 0:
            return
        normal = [d/length for d in direction]

        # Вычисляем глубину проникновения
        size1 = obj1.calculate_bounding_radius()
        size2 = obj2.calculate_bounding_radius()
        penetration = (size1 + size2) - length

        # Если проникновение слишком маленькое - пропускаем
        if penetration < 0.001:
            return

        # Немедленная коррекция позиций для предотвращения застревания
        correction = penetration * 1  # Чуть больше, чтобы точно разделить объекты
        
        if not params1['is_static'] and not params2['is_static']:
            ratio1 = m2 / (m1 + m2)
            ratio2 = m1 / (m1 + m2)
        elif params1['is_static']:
            ratio1, ratio2 = 0, 1
        else:
            ratio1, ratio2 = 1, 0

        # Применяем коррекцию позиции
        if not params1['is_static']:
            for i in range(3):
                pos1[i] -= normal[i] * correction * ratio1
            obj1.position = tuple(pos1)

        if not params2['is_static']:
            for i in range(3):
                pos2[i] += normal[i] * correction * ratio2
            obj2.position = tuple(pos2)

        # Вычисляем относительную скорость
        rel_velocity = [v1[i] - v2[i] for i in range(3)]
        normal_velocity = sum(rv * n for rv, n in zip(rel_velocity, normal))

        # Если объекты удаляются друг от друга - пропускаем
        if normal_velocity > 0:
            return

        # Увеличиваем коэффициент восстановления для более упругих столкновений
        restitution = min(params1['restitution'], params2['restitution']) * 1.2

        # Вычисляем импульс с увеличенной силой отталкивания
        j = -(1 + restitution) * normal_velocity
        if not params1['is_static'] and not params2['is_static']:
            j /= (1/m1 + 1/m2)
        elif params1['is_static']:
            j *= m2
        else:
            j *= m1

        # Применяем импульс к скоростям
        if not params1['is_static']:
            for i in range(3):
                v1[i] += (j * normal[i]) / m1
        
        if not params2['is_static']:
            for i in range(3):
                v2[i] -= (j * normal[i]) / m2

        # Обновляем скорости в параметрах
        if not params1['is_static']:
            params1['velocity'] = tuple(v1)
        if not params2['is_static']:
            params2['velocity'] = tuple(v2)

        self.logger.debug(f"Коллизия обработана: v1={v1}, v2={v2}, penetration={penetration}")

    def set_gravity(self, gravity: tuple) -> None:
        """Устанавливает вектор гравитации"""
        self.gravity = gravity
        for obj in self.objects.values():
            if not obj['is_static']:
                obj['acceleration'] = list(gravity)

    def _calculate_penetration(self, obj1: Mesh3D, obj2: Mesh3D) -> list:
        """Вычисляет глубину проникновения между двумя объектами по каждой оси"""
        params1 = self.physics_params[obj1.name]
        params2 = self.physics_params[obj2.name]

        b1 = params1['bounds']
        b2 = params2['bounds']

        # Вычисляем перекрытие по каждой оси
        penetrations = [
            min(b1[3], b2[3]) - max(b1[0], b2[0]),  # X axis
            min(b1[4], b2[4]) - max(b1[1], b2[1]),  # Y axis
            min(b1[5], b2[5]) - max(b1[2], b2[2])  # Z axis
        ]

        # Возвращаем только положительные значения проникновения
        return [p if p > 0 else 0 for p in penetrations]