import json
import numpy as np
from itertools import product


def generate_test_scene():
    scene = {"objects": {}}

    # Параметры сетки
    grid_size = 4  # 4x4x4 = 64 объекта
    spacing = 3.0  # Расстояние между объектами

    # Создаем сетку объектов
    for i, j, k in product(range(grid_size), repeat=3):
        # Генерируем имя объекта
        name = f"Куб_{i}_{j}_{k}"

        # Вычисляем позицию
        x = (i - grid_size / 2) * spacing
        y = (j - grid_size / 2) * spacing
        z = (k - grid_size / 2) * spacing

        # Генерируем цвет на основе позиции
        r = i / (grid_size - 1)
        g = j / (grid_size - 1)
        b = k / (grid_size - 1)

        # Создаем объект
        scene["objects"][name] = {
            "type": "mesh",
            "vertices": [
                [-1.0, -1.0, -1.0],
                [1.0, -1.0, -1.0],
                [1.0, 1.0, -1.0],
                [-1.0, 1.0, -1.0],
                [-1.0, -1.0, 1.0],
                [1.0, -1.0, 1.0],
                [1.0, 1.0, 1.0],
                [-1.0, 1.0, 1.0]
            ],
            "faces": [
                [0, 1, 2], [0, 2, 3],  # front
                [4, 5, 6], [4, 6, 7],  # back
                [0, 1, 5], [0, 5, 4],  # bottom
                [2, 3, 7], [2, 7, 6],  # top
                [0, 3, 7], [0, 7, 4],  # left
                [1, 2, 6], [1, 6, 5]  # right
            ],
            "color": [r, g, b, 1.0],
            "visible": True,
            "transform": {
                "position": [x, y, z],
                "rotation": [0, 0, 0],
                "scale": [1.0, 1.0, 1.0]
            },
            "animation": {
                "move_script": f"result = ({x} + sin(t), {y}, {z})" if i % 2 == 0 else "",
                "rotation_script": f"result = (0, 45*t, 0)" if j % 2 == 0 else "",
                "enabled": (i + j + k) % 3 == 0  # Каждый третий объект анимирован
            }
        }

    # Сохраняем в файл
    with open('test_scene.json', 'w', encoding='utf-8') as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    generate_test_scene()
