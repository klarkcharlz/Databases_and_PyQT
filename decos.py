from functools import wraps
import inspect


class Log:
    def __init__(self, logger):
        """
        :param logger: Параметр декоратора обьект логгера
        """
        self.logger = logger

    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):
            # пока отключил что бы небыло спама
            # traceback_ = inspect.stack()[1][3]
            # if traceback_ != "<module>":
            #     self.logger.info(f"Функция {func.__name__} была вызвана из функции {traceback_}")
            res = func(*args, **kwargs)
            self.logger.info(f"Log {func.__name__}({args}, {kwargs}) = {res}.")
            return res
        return decorated
