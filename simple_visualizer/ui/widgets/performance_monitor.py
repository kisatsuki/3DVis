import time
import logging
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QTimer

class PerformanceMonitor(QLabel):
    """
    Виджет для отображения информации о производительности
    """
    
    def __init__(self, parent=None):
        """Инициализация монитора производительности"""
        super().__init__(parent)
        self.logger = logging.getLogger("simple_visualizer.ui.widgets.performance_monitor")
        
        # Настраиваем внешний вид
        self.setStyleSheet("background-color: rgba(0, 0, 0, 50); color: white; padding: 5px;")
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # Данные для расчета FPS
        self.frame_times = []
        self.max_history = 30
        self.last_frame_time = time.time()
        self.current_fps = 0
        self.avg_fps = 0
        
        # Таймер для обновления текста
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_text)
        self.update_timer.start(500)  # 0.5 секунды
        
        # Устанавливаем начальный текст
        self.setText("FPS: 0.0")
        
        # Запускаем таймер для эмуляции обновления кадров
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_frame_time)
        self.frame_timer.start(16)  # ~60 FPS
        
        self.show_vertices = False
        self.vertex_count = 0
        
        self.logger.info("Монитор производительности инициализирован")
    
    def update_frame_time(self):
        """Обновляет информацию о времени кадра"""
        # Вычисляем время кадра
        current_time = time.time()
        dt = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        # Добавляем новое время кадра
        self.frame_times.append(dt)
        
        # Ограничиваем количество сохраненных измерений
        if len(self.frame_times) > self.max_history:
            self.frame_times.pop(0)
        
        # Рассчитываем средние значения, избегая деления на ноль
        if self.frame_times:
            # Безопасно вычисляем средний FPS, избегая деления на нулевые значения времени
            valid_times = [t for t in self.frame_times if t > 0]
            if valid_times:
                self.avg_fps = sum([1.0/t for t in valid_times]) / len(valid_times)
            else:
                self.avg_fps = 0
        else:
            self.avg_fps = 0
            
        # Обновляем текущий FPS
        if dt > 0:
            self.current_fps = 1.0 / dt
        else:
            self.current_fps = 0
    
    def show_vertex_stats(self, vertex_count: int):
        """Показывает статистику по вершинам"""
        self.show_vertices = True
        self.vertex_count = vertex_count
    
    def hide_vertex_stats(self):
        """Скрывает статистику по вершинам"""
        self.show_vertices = False
    
    def update_text(self):
        """Обновляет отображаемый текст"""
        base_text = f"FPS: {self.current_fps:.1f} (avg: {self.avg_fps:.1f})"
        if self.show_vertices:
            self.setText(f"{base_text} | Активных вершин: {self.vertex_count:,}")
        else:
            self.setText(base_text) 