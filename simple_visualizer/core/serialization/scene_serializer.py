import json
import logging
import time
from pathlib import Path
import numpy as np
from typing import Dict, Any, Optional, Tuple

class SceneSerializer:
    """
    Класс для сериализации и десериализации сцены.
    Отвечает за сохранение и загрузку состояния сцены в/из файла.
    """

    def __init__(self, settings_path: Path = None):
        """
        Инициализация сериализатора сцены.
        
        Args:
            settings_path (Path): Путь к директории настроек. Если не указан,
                                будет использована домашняя директория пользователя.
        """
        self.logger = logging.getLogger("simple_visualizer.core.serialization.scene_serializer")
        
        # Инициализируем путь к настройкам
        self.settings_path = settings_path or Path.home() / '.simple_visualizer'
        self.settings_path.mkdir(exist_ok=True)
        
        # Устанавливаем путь к файлу сцены
        self.scene_file = self.settings_path / 'last_scene.json'
        
        self.logger.info(f"SceneSerializer инициализирован, файл сцены: {self.scene_file}")

    def save_scene(self, objects: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Сохраняет текущее состояние сцены в файл JSON.

        Args:
            objects (Dict[str, Any]): Словарь объектов сцены для сохранения

        Returns:
            Tuple[bool, str]: (успех операции, сообщение о результате)
        """
        try:
            # Проверяем, существует ли директория для сохранения
            if not self.settings_path.exists():
                self.logger.info(f"Создаем директорию для сохранения: {self.settings_path}")
                self.settings_path.mkdir(parents=True, exist_ok=True)

            # Создаем структуру данных сцены
            scene_data = {
                "version": "1.0",
                "timestamp": time.time(),
                "objects": {}
            }

            # Сохраняем объекты
            objects_count = 0
            for name, obj in objects.items():
                try:
                    # Получаем словарь с данными объекта
                    obj_data = obj.to_dict()
                    # Добавляем имя объекта в данные (для совместимости)
                    if 'name' not in obj_data:
                        obj_data['name'] = name
                    # Сохраняем в структуру сцены
                    scene_data["objects"][name] = obj_data
                    objects_count += 1
                    self.logger.debug(f"Объект '{name}' сохранен")
                except Exception as e:
                    self.logger.error(f"Ошибка при сериализации объекта '{name}': {e}")
                    # Продолжаем с другими объектами

            # Если нет объектов для сохранения, сообщаем об этом
            if objects_count == 0:
                return False, "Нет объектов для сохранения"

            # Сохраняем в файл с форматированием
            with open(self.scene_file, 'w', encoding='utf-8') as f:
                json.dump(scene_data, f, indent=2, ensure_ascii=False)

            success_msg = f"Сцена сохранена в {self.scene_file} ({objects_count} объектов)"
            self.logger.info(success_msg)
            return True, success_msg

        except Exception as e:
            error_msg = f"Ошибка при сохранении сцены: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def load_scene(self) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Загружает сцену из файла JSON.

        Returns:
            Tuple[Optional[Dict[str, Any]], str]: (загруженные данные сцены, сообщение о результате)
        """
        if not self.scene_file.exists():
            msg = f"Файл сцены не найден: {self.scene_file}"
            self.logger.warning(msg)
            return None, msg

        try:
            # Загружаем данные из файла
            with open(self.scene_file, 'r', encoding='utf-8') as f:
                try:
                    scene_data = json.load(f)
                except json.JSONDecodeError as e:
                    error_msg = f"Ошибка декодирования JSON: {e}"
                    self.logger.error(error_msg)
                    return None, error_msg

            # Определяем формат данных (поддержка старых форматов)
            if isinstance(scene_data, dict) and "objects" in scene_data:
                objects_data = scene_data["objects"]
            elif isinstance(scene_data, dict):
                self.logger.info("Обнаружен старый формат файла сцены")
                objects_data = scene_data
            else:
                error_msg = "Некорректный формат данных в файле сцены"
                self.logger.error(error_msg)
                return None, error_msg

            success_msg = f"Данные сцены успешно загружены из {self.scene_file}"
            self.logger.info(success_msg)
            return objects_data, success_msg

        except Exception as e:
            error_msg = f"Ошибка при загрузке сцены: {e}"
            self.logger.error(error_msg)
            return None, error_msg 