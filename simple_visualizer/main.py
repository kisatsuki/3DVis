import sys
import logging
from PySide6.QtWidgets import QApplication

from utils.logging_config import setup_logging
from ui.main_window import MainWindow

if __name__ == "__main__":
    # Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)

    # Создаем приложение
    app = QApplication(sys.argv)
    app.setApplicationName("SimpleVisualizer")

    # Создаем и показываем главное окно
    logger.info("Запуск SimpleVisualizer")
    window = MainWindow()
    window.show()

    # Запускаем основной цикл приложения
    sys.exit(app.exec())
