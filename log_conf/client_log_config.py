"""Клиентский логгер"""

import logging
import os
import sys


# Определить формат сообщений
# дата уровень имя сообщение
FORMAT = logging.Formatter('%(asctime)-25s  %(levelname)-10s  %(name)-10s  %(message)s')
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs/client.log'))

# Создать обработчик, который выводит сообщения в файл
client_log_hand = logging.FileHandler(LOGS_PATH)
client_log_hand.setFormatter(FORMAT)

# обработчик который выводит сообщение в консоль
client_terminal_log = logging.StreamHandler(sys.stderr)
client_terminal_log.setFormatter(FORMAT)

# Создать регистратор
client_log = logging.getLogger('client')
client_log.setLevel(logging.INFO)
client_log.addHandler(client_log_hand)
client_log.addHandler(client_terminal_log)
