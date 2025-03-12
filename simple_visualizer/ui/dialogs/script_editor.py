from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QPushButton,
                              QLabel, QHBoxLayout, QGroupBox, QListWidget,
                              QSplitter, QTextEdit, QInputDialog, QComboBox, 
                              QToolButton, QMenu, QCheckBox)
from PySide6.QtCore import Qt
from ..widgets.code_editor import CodeEditor
import os
import json
import logging
import math

class ScriptEditorDialog(QDialog):
    """Диалог для редактирования скрипта анимации"""
    
    def __init__(self, rotation_script="", move_script="", use_relative=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор скриптов анимации")
        self.setModal(True)
        self.resize(800, 600)
        
        # Создаем layout
        layout = QVBoxLayout(self)
        
        # Добавляем описание
        info_label = QLabel(
            "Определите функции движения и вращения объекта.\n"
            "Доступные переменные:\n"
            "  t - время (в секундах)\n"
            "  dt - время между кадрами\n"
            "  x, y, z - текущие координаты\n"
            "  rx, ry, rz - текущие углы поворота\n"
            "Функции должны возвращать кортеж (x, y, z)"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Добавляем флажок для относительных координат
        self.relative_checkbox = QCheckBox("Использовать относительные координаты")
        self.relative_checkbox.setChecked(use_relative)
        self.relative_checkbox.setToolTip(
            "Если включено, анимация будет выполняться относительно текущего положения объекта.\n"
            "Например, result = (0, sin(t), 0) не переместит объект в центр координат."
        )
        layout.addWidget(self.relative_checkbox)
        
        # Редактор для движения
        move_group = QGroupBox("Функция движения")
        move_layout = QVBoxLayout()
        move_layout.addWidget(QLabel("Функция движения:"))
        self.move_editor = CodeEditor()
        self.move_editor.setPlainText(move_script)
        self.move_editor.on_text_changed()
        move_layout.addWidget(self.move_editor)
        move_group.setLayout(move_layout)
        layout.addWidget(move_group)
        
        # Редактор для вращения
        rotation_group = QGroupBox("Функция вращения")
        rotation_layout = QVBoxLayout()
        rotation_layout.addWidget(QLabel("Функция вращения:"))
        self.rotation_editor = CodeEditor()
        self.rotation_editor.setPlainText(rotation_script)
        self.rotation_editor.on_text_changed()
        rotation_layout.addWidget(self.rotation_editor)
        rotation_group.setLayout(rotation_layout)
        layout.addWidget(rotation_group)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Применить")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def get_scripts(self):
        """Возвращает текст скриптов и настройки"""
        return {
            'move': self.move_editor.text(),
            'rotation': self.rotation_editor.text(),
            'use_relative': self.relative_checkbox.isChecked()
        } 