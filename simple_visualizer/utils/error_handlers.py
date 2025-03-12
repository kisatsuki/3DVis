import functools
import logging

def handle_object_operation(logger=None):
    """Декоратор для обработки ошибок операций с объектами"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Получаем имя объекта из первого аргумента (после self)
                obj_name = args[1] if len(args) > 1 else kwargs.get('name', 'unknown')
                error_msg = f"Ошибка при выполнении {func.__name__} для объекта '{obj_name}': {e}"
                
                # Используем переданный логгер или создаем стандартный
                log = logger or logging.getLogger("simple_visualizer.error_handler")
                log.error(error_msg)
                
                # Для методов bool возвращаем False, иначе None
                return False if func.__annotations__.get('return') == bool else None
        return wrapper
    return decorator 