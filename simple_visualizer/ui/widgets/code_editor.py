import re
from PySide6.QtWidgets import (QPlainTextEdit, QWidget, QTextEdit,
                               QCompleter, QVBoxLayout, QToolTip)
from PySide6.QtGui import (QTextCharFormat, QSyntaxHighlighter,
                           QColor, QFont, QTextCursor, QPainter,
                           QTextFormat, QBrush)
from PySide6.QtCore import Qt, Signal, QRect, QSize, QStringListModel, QPoint, QTimer, QEvent


class PythonHighlighter(QSyntaxHighlighter):
    """Подсветка синтаксиса Python"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.formats = {}

        # Ключевые слова Python
        keywords = ['and', 'as', 'assert', 'break', 'class', 'continue', 'def',
                    'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
                    'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
                    'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True',
                    'try', 'while', 'with', 'yield']

        # Встроенные функции
        builtins = ['abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes',
                    'chr', 'complex', 'dict', 'float', 'int', 'len', 'list',
                    'max', 'min', 'range', 'set', 'str', 'sum', 'tuple', 'type']

        # Специальные функции для анимации с документацией
        animation_funcs = {
            'sin': 'sin(x) - синус угла x (в радианах)',
            'cos': 'cos(x) - косинус угла x (в радианах)',
            'tan': 'tan(x) - тангенс угла x (в радианах)',
            'pi': 'константа π (3.14159...)',
            'sqrt': 'sqrt(x) - квадратный корень из x',
            'pow': 'pow(x, y) - x в степени y',
            't': 'время в секундах с начала анимации',
            'dt': 'время между кадрами в секундах',
            'result': 'переменная для возврата результата (должна быть кортежем из 3 значений)'
        }

        # Форматы для разных типов токенов
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#7A3E9D"))  # Приглушенный фиолетовый
        keyword_format.setFontWeight(QFont.Bold)

        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#277299"))  # Приглушенный синий

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#0E9C5A"))  # Приглушенный зеленый

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#BD6200"))  # Приглушенный оранжевый

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#71787C"))  # Серый
        comment_format.setFontItalic(True)

        animation_format = QTextCharFormat()
        animation_format.setForeground(QColor("#AF0EA0"))  # Яркий фиолетовый
        animation_format.setFontWeight(QFont.Bold)

        # Применение форматов
        self.add_mapping(r'\b(?:' + '|'.join(keywords) + r')\b', keyword_format)
        self.add_mapping(r'\b(?:' + '|'.join(builtins) + r')\b', builtin_format)
        self.add_mapping(r'\b(?:' + '|'.join(animation_funcs.keys()) + r')\b', animation_format)
        self.add_mapping(r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', number_format)
        self.add_mapping(r'\".*?\"|\'.*?\'', string_format)
        self.add_mapping(r'#[^\n]*', comment_format)

        # Сохраняем документацию по функциям
        self.function_docs = animation_funcs

    def add_mapping(self, pattern, format):
        self.formats[pattern] = format

    def highlightBlock(self, text):
        for pattern, format in self.formats.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, format)


class CodeEditor(QPlainTextEdit):
    """Редактор кода с подсветкой синтаксиса и нумерацией строк"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Настройка шрифта
        font = QFont()
        font.setFamily('Consolas')  # Моноширинный шрифт для кода
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)

        # Настройка отступов
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))

        # Установка цветов
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #DCDCDC;
                border: 1px solid #3F3F3F;
            }
        """)

        # Создание области номеров строк
        self.line_number_area = LineNumberArea(self)

        # Настройка подсветки синтаксиса
        self.highlighter = PythonHighlighter(self.document())

        # Индикатор ошибок синтаксиса
        self.error_line = None
        self.error_message = ""
        self.error_format = QTextCharFormat()
        # Стиль подчеркивания как в PyCharm
        self.error_format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
        self.error_format.setUnderlineColor(QColor("#FF0000"))  # Красное подчеркивание

        # Таймер для отложенной проверки синтаксиса
        self.syntax_check_timer = QTimer(self)
        self.syntax_check_timer.setSingleShot(True)
        self.syntax_check_timer.setInterval(500)  # Проверка через 500 мс после последнего изменения
        self.syntax_check_timer.timeout.connect(self.check_syntax)

        # Инициализация экстра-выделений
        self.syntax_error_selections = []

        # Установка соединений для обновления номеров строк
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        # Обновление проверки синтаксиса при изменении текста
        self.textChanged.connect(self.on_text_changed)

        # Инициализация ширины области номеров строк
        self.update_line_number_area_width(0)

        # Подсветка текущей строки
        self.highlight_current_line()

        # Добавление автодополнения
        self.setup_completer()

        # Словарь для отслеживания скобок и кавычек
        self.brackets = {
            '(': ')',
            '[': ']',
            '{': '}',
            '"': '"',
            "'": "'"
        }

    def setup_completer(self):
        """Настройка автодополнения"""
        # Создаем список слов для автодополнения
        words = list(self.highlighter.function_docs.keys())
        words.extend([
            'x', 'y', 'z',  # позиция
            'rx', 'ry', 'rz',  # вращение
            't', 'dt',  # время
            'for', 'if', 'while', 'return', 'True', 'False', 'None'
        ])

        # Создаем и настраиваем комплитер
        self.completer = QCompleter(words, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self)
        self.completer.activated.connect(self.insert_completion)

    def insert_completion(self, completion):
        """Вставляет выбранное автодополнение"""
        # Получаем текущую позицию и текст, который нужно заменить
        cursor = self.textCursor()
        chars_to_replace = completion.length() - self.completer.completionPrefix().length()
        cursor.movePosition(QTextCursor.Left)
        cursor.movePosition(QTextCursor.EndOfWord)
        cursor.insertText(completion.right(chars_to_replace))
        self.setTextCursor(cursor)

    def text(self):
        """Возвращает текст редактора"""
        return self.toPlainText()

    def set_text(self, text):
        """Устанавливает текст редактора"""
        self.setPlainText(text)

    def lineNumberAreaWidth(self):
        """Вычисляет ширину области номеров строк"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1

        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, newBlockCount):
        """Обновляет отступ для номеров строк"""
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Обновляет область номеров строк при прокрутке"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Обработка изменения размера виджета"""
        super().resizeEvent(event)

        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )

    def highlight_current_line(self):
        """Подсвечивает текущую строку"""
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()

            line_color = QColor("#2A2A2A")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()

            extra_selections.append(selection)

        # Добавляем подсветку строки с ошибкой, если есть
        if self.error_line is not None:
            selection = QTextEdit.ExtraSelection()
            selection.format = self.error_format
            selection.cursor = QTextCursor(self.document().findBlockByLineNumber(self.error_line))

            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def set_error(self, line_number):
        """Устанавливает подчеркивание ошибки в указанной строке"""
        self.error_line = line_number

        # Применяем подчеркивание к строке с ошибкой
        cursor = QTextCursor(self.document().findBlockByNumber(line_number))
        cursor.select(QTextCursor.LineUnderCursor)

        # Создаем формат с подчеркиванием
        selection = QTextEdit.ExtraSelection()
        selection.format = self.error_format
        selection.cursor = cursor

        # Применяем подчеркивание
        self.setExtraSelections([selection] + self.extraSelections())

    def clear_error(self):
        """Очищает подчеркивание ошибок"""
        self.error_line = None
        self.error_message = ""
        self.syntax_error_selections = []
        self.update_extra_selections()
        self.setToolTip("")

    def update_extra_selections(self):
        """Обновляет все экстра-выделения, сохраняя как подсветку текущей строки, так и ошибки"""
        # Получаем текущие выделения (текущая строка)
        current_line_selections = []
        for selection in self.extraSelections():
            if selection.format != self.error_format:
                current_line_selections.append(selection)

        # Объединяем выделения текущей строки и ошибок
        all_selections = current_line_selections + self.syntax_error_selections
        self.setExtraSelections(all_selections)

    def on_text_changed(self):
        """Запускает отложенную проверку синтаксиса при изменении текста"""
        self.syntax_check_timer.start()

    def check_syntax(self):
        """Проверяет синтаксис Python и подчеркивает ошибки"""
        code = self.toPlainText()
        
        # Очищаем старые ошибки
        self.clear_error()
        
        # Если код пустой, нет смысла проверять
        if not code.strip():
            return
        
        # Проверяем незакрытые скобки и кавычки
        brackets_stack = []
        open_brackets = {'(': ')', '[': ']', '{': '}'}
        close_brackets = {')', ']', '}'}
        quote_type = None
        
        error_lines = []
        line_num = 0
        column_num = 0
        
        for i, char in enumerate(code):
            # Обновляем номер строки и колонки
            if char == '\n':
                line_num += 1
                column_num = 0
            else:
                column_num += 1
            
            # Обработка кавычек
            if char in ('"', "'") and (quote_type is None or char == quote_type):
                if quote_type is None:
                    quote_type = char
                else:
                    quote_type = None
                continue
            
            # Пропускаем символы в строках
            if quote_type is not None:
                continue
            
            # Проверяем скобки
            if char in open_brackets:
                brackets_stack.append((char, line_num, column_num))
            elif char in close_brackets:
                if not brackets_stack or open_brackets[brackets_stack[-1][0]] != char:
                    # Несоответствие скобок - ошибка
                    error_lines.append((line_num, column_num, f"Неожиданная скобка '{char}'"))
                else:
                    brackets_stack.pop()
        
        # Проверяем незакрытые скобки
        for bracket, line, col in brackets_stack:
            error_lines.append((line, col, f"Незакрытая скобка '{bracket}'"))
        
        # Если незакрытые кавычки
        if quote_type is not None:
            error_lines.append((line_num, column_num, f"Незакрытая кавычка '{quote_type}'"))
        
        # Проверка стандартного парсера Python
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            error_line = e.lineno - 1
            error_column = e.offset - 1 if e.offset else 0
            error_message = str(e)
            
            # Добавляем в список если не пересекается с уже найденными ошибками
            found = False
            for i, (line, col, _) in enumerate(error_lines):
                if line == error_line:
                    found = True
                    error_lines[i] = (line, col, error_message)
                    break
            
            if not found:
                error_lines.append((error_line, error_column, error_message))
        
        # Очищаем прошлые выделения ошибок
        self.syntax_error_selections = []
        
        # Добавляем выделения для каждой обнаруженной ошибки
        for line, column, message in error_lines:
            if line >= 0 and line < self.document().blockCount():
                block = self.document().findBlockByNumber(line)
                
                # Создаем выделение для этой строки
                cursor = QTextCursor(block)
                
                if column >= 0 and column < len(block.text()):
                    # Подчеркиваем только символ или токен с ошибкой
                    cursor.setPosition(block.position() + column)
                    
                    # Определяем длину токена
                    if column < len(block.text()):
                        # Для скобок и кавычек - один символ
                        if block.text()[column] in '()[]{}\'\"':
                            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
                        else:
                            # Для других токенов - до первого разделителя
                            token_pattern = r'[^\s\(\)\[\]\{\}\,\:\;\'\"\=\+\-\*\/\%\&\|\^\~\<\>\!]+'
                            match = re.search(token_pattern, block.text()[column:])
                            if match:
                                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, match.end())
                            else:
                                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
                else:
                    # Если колонка не определена точно, подчеркиваем всю строку
                    cursor.select(QTextCursor.LineUnderCursor)
                
                # Создаем выделение
                selection = QTextEdit.ExtraSelection()
                selection.format = self.error_format
                selection.cursor = cursor
                selection.format.setToolTip(message)  # Добавляем сообщение об ошибке
                
                self.syntax_error_selections.append(selection)
        
        # Обновляем выделения
        self.update_extra_selections()
        
        # Показываем первую ошибку в подсказке
        if error_lines:
            self.error_line = error_lines[0][0]
            self.error_message = error_lines[0][2]
            self.setToolTip(f"Ошибка синтаксиса: {self.error_message}")

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        # Проверяем автодополнение
        if event.key() == Qt.Key_Tab and self.completer and self.completer.popup().isVisible():
            self.completer.insertText(self.completer.currentCompletion())
            self.completer.popup().hide()
            return

        # Автоматическое удаление парных скобок и кавычек
        if event.key() == Qt.Key_Backspace:
            cursor = self.textCursor()
            if not cursor.hasSelection():  # Если нет выделения
                pos = cursor.position()
                if pos > 0 and pos < len(self.toPlainText()):
                    # Получаем символ перед курсором и после курсора
                    char_before = self.toPlainText()[pos - 1:pos]
                    char_after = self.toPlainText()[pos:pos + 1]

                    # Проверяем, образуют ли они пару
                    opening_chars = self.brackets.keys()
                    closing_chars = self.brackets.values()

                    if char_before in opening_chars and char_after == self.brackets[char_before]:
                        # Удаляем оба символа
                        cursor.deleteChar()  # Удаляем символ после курсора
                        cursor.deletePreviousChar()  # Удаляем символ перед курсором
                        return

        # Автоматические отступы
        if event.key() == Qt.Key_Return:
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            indent = re.match(r'(\s*)', text).group(1)

            # Увеличиваем отступ после двоеточия
            if text.strip().endswith(':'):
                indent += '    '

            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return

        # Автоматическое добавление закрывающей скобки или кавычки
        if event.text() in self.brackets:
            cursor = self.textCursor()
            block = cursor.block()

            # Особая обработка для кавычек
            if event.text() in ['"', "'"]:
                # Проверяем, есть ли уже закрывающая кавычка
                char_after_cursor = self.toPlainText()[
                                    cursor.position():cursor.position() + 1] if cursor.position() < len(
                    self.toPlainText()) else ""

                # Проверяем, не находимся ли мы уже внутри строки противоположного типа кавычек
                # Простая эвристика: считаем кавычки от начала строки до текущей позиции
                line_to_cursor = block.text()[:cursor.positionInBlock()]

                # Если мы внутри строки с другим типом кавычек, не добавляем закрывающую
                opposite_quote = "'" if event.text() == '"' else '"'
                if line_to_cursor.count(opposite_quote) % 2 == 1:
                    super().keyPressEvent(event)
                    return

                # Если после курсора уже есть такая же кавычка, просто перемещаем курсор
                if char_after_cursor == event.text():
                    cursor.movePosition(QTextCursor.Right)
                    self.setTextCursor(cursor)
                    return

            # Добавляем открывающую и закрывающую скобку/кавычку
            cursor.insertText(event.text() + self.brackets[event.text()])
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 1)
            self.setTextCursor(cursor)
            return

        # Проверяем на Ctrl+Space для вызова автодополнения
        if event.key() == Qt.Key_Space and event.modifiers() == Qt.ControlModifier:
            cursor = self.textCursor()
            cursor.select(QTextCursor.WordUnderCursor)
            prefix = cursor.selectedText()

            self.completer.setCompletionPrefix(prefix)
            popup = self.completer.popup()

            # Показываем подсказку рядом с курсором
            cursor_rect = self.cursorRect()

            # Если есть подходящие варианты, показываем выпадающий список
            if self.completer.completionCount() > 0:
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
                popup.setGeometry(
                    cursor_rect.x(), cursor_rect.y() + self.fontMetrics().height(),
                    300, 200
                )
                popup.show()
            return

        # Показываем подсказку для функций
        if event.key() == Qt.Key_Escape and QToolTip.isVisible():
            QToolTip.hideText()
            return

        # Подсказка при остановке на функции
        if event.key() == Qt.Key_F1:
            cursor = self.textCursor()
            cursor.select(QTextCursor.WordUnderCursor)
            word = cursor.selectedText()

            if word in self.highlighter.function_docs:
                QToolTip.showText(
                    self.mapToGlobal(self.cursorRect().bottomRight()),
                    self.highlighter.function_docs[word],
                    self
                )
                return

        super().keyPressEvent(event)

        # Динамическая проверка синтаксиса
        if event.key() in (Qt.Key_Return, Qt.Key_Space, Qt.Key_Period, Qt.Key_Semicolon):
            self.check_syntax()

    def event(self, event):
        """Обрабатывает события, включая подсказки при наведении на ошибки"""
        if event.type() == QEvent.ToolTip and self.error_line is not None and self.error_message:
            cursor = self.cursorForPosition(event.pos())
            block_number = cursor.blockNumber()

            # Проверяем, находится ли курсор на строке с ошибкой
            if block_number == self.error_line:
                QToolTip.showText(event.globalPos(), f"Ошибка синтаксиса: {self.error_message}")
            else:
                QToolTip.hideText()

        return super().event(event)


class LineNumberArea(QWidget):
    """Область с номерами строк"""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        """Подсказка о размере виджета"""
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        """Отрисовка номеров строк"""
        painter = QPainter(self)
        # Меняем цвет фона области с номерами строк
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(
            self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                # Если это текущий блок, выделяем номер строки
                if block_number == self.editor.textCursor().blockNumber():
                    painter.setPen(QColor("#FFFFFF"))
                else:
                    painter.setPen(QColor("#858585"))
                painter.drawText(0, int(top), self.width() - 2,
                                 self.editor.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            block_number += 1