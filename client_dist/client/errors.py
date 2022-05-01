"""Пользовательские исключения"""


class ServerError(Exception):
    """Ошибка со стороны сервера."""
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text
