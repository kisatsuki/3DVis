import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from simple_visualizer.core.simple_shapes import create_sphere_object, create_box_object, create_cylinder_object, create_cone_object, create_torus_object
from simple_visualizer.core.viewport import Viewport3D
from simple_visualizer.core.physics_engine import PhysicsEngine

# Создаем приложение
app = QApplication(sys.argv)

# Создаем вьюпорт
viewport = Viewport3D()
viewport.resize(800, 600)
viewport.show()

# Создаем физический движок
physics = PhysicsEngine()

# Связываем сигнал обновления коллайдеров
physics.collider_updated.connect(viewport.update_collider)
# Обрабатываем запросы на обновление коллайдеров
viewport.collider_request.connect(lambda name: physics._emit_collider_update(name))

# Создаем объекты с разными типами коллайдеров
sphere = create_sphere_object('sphere', radius=1.0, position=(-3, 0, 0), color=(0, 0.7, 0, 1.0))
box = create_box_object('box', size=(1.0, 0.8, 1.2), position=(0, 0, 0), color=(0, 0, 0.7, 1.0))
cylinder = create_cylinder_object('cylinder', radius=0.7, height=1.5, position=(3, 0, 0), color=(0.7, 0, 0, 1.0))
cone = create_cone_object('cone', radius=0.8, height=1.8, position=(0, 3, 0), color=(0.7, 0.7, 0, 1.0))
torus = create_torus_object('torus', major_radius=1.0, minor_radius=0.3, position=(0, -3, 0), color=(0.7, 0, 0.7, 1.0))

# Создаем объекты в сцене и регистрируем в физическом движке
for obj in [sphere, box, cylinder, cone, torus]:
    obj.create_view_item(viewport)
    physics.register_object(obj)

# Включаем отображение коллайдеров (после создания объектов)
viewport.set_debug_colliders(True)

# Запускаем таймер для обновления физики
timer = QTimer()
timer.timeout.connect(physics.update)
timer.start(16)  # ~60 FPS

# Запускаем главный цикл приложения
sys.exit(app.exec()) 