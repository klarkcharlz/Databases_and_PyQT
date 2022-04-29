"""Логгер сервера"""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler


# Определить формат сообщений
# дата уровень имя сообщение
FORMAT = logging.Formatter('%(asctime)-25s %(levelname)-10s %(name)-10s %(message)s')
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs/server.log'))

# Создать обработчик, который выводит сообщения в файл
server_log_hand = logging.FileHandler(LOGS_PATH)
server_log_hand.setFormatter(FORMAT)

# Создать обработчик, который выводит сообщения в консоль
server_terminal_log = logging.StreamHandler(sys.stderr)
server_terminal_log.setFormatter(FORMAT)

# TimedRotating обработчик
BACKUP_LOGS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', "logs/backup/server/server.log"))
time_handler = TimedRotatingFileHandler(BACKUP_LOGS,
                                        when='d',
                                        interval=3,
                                        backupCount=5)

# Создать регистратор
server_log = logging.getLogger('server')
server_log.setLevel(logging.INFO)
server_log.addHandler(server_log_hand)
server_log.addHandler(time_handler)
server_log.addHandler(server_terminal_log)
