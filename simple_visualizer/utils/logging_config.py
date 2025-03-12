import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_level=logging.INFO, log_dir="logs"):
    """
    Настраивает систему логирования приложения
    
    Args:
        log_level: Уровень логирования 
        log_dir: Директория для файлов логов
    """
    # Создаем директорию для логов если она не существует
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Формат логирования
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Обработчик для вывода в файл
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10 МБ
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Добавляем обработчики к корневому логгеру
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Определяем основные логгеры для модулей
    loggers = {
        'ui': logging.getLogger('simple_visualizer.ui'),
        'core': logging.getLogger('simple_visualizer.core'),
        'utils': logging.getLogger('simple_visualizer.utils')
    }
    
    # Настраиваем уровни логгирования для модулей
    loggers['ui'].setLevel(logging.INFO)
    loggers['core'].setLevel(logging.DEBUG)  # Более детальное логирование для ядра
    loggers['utils'].setLevel(logging.INFO)
    
    logging.info("Система логирования инициализирована")
    return loggers 