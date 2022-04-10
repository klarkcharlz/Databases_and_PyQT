from socket import socket, AF_INET, SOCK_STREAM
import argparse
from time import time, sleep
from json import dumps
import threading
import sys
import dis

from log_conf.client_log_config import client_log
from decos import Log

parser = argparse.ArgumentParser(description='JSON instant messaging client.')
parser.add_argument(
    '-addr',
    type=str,
    default="localhost",
    help='Server IP (default: localhost)'
)
parser.add_argument(
    '-port',
    type=int,
    default=7777,
    help='Server port (default: 7777)'
)
args = parser.parse_args()


class ClientVerifier(type):
    """
    отсутствие вызовов accept и listen для сокетов;
    использование сокетов для работы по TCP;
    """

    def __init__(cls, class_name, bases, class_dict):
        methods = []
        for func in class_dict:
            try:
                ret = dis.get_instructions(class_dict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_METHOD':
                        if i.argval not in methods:
                            methods.append(i.argval)
        for command in ('accept', 'listen'):
            if command in methods:
                raise TypeError('В классе обнаружено использование запрещённого метода')
        if '__receive_msg' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError('Отсутствуют вызовы функций, работающих с сокетами.')
        super().__init__(class_name, bases, class_dict)


class CustomClient(metaclass=ClientVerifier):

    def __init__(self, family: int, type_: int, timeout_=None) -> None:
        self.client = socket(family, type_)
        if timeout_:
            self.client.settimeout(timeout_)
        self.con = False
        self.addr = args.addr
        self.port = args.port
        self.name = self.get_name()
        self.run_flag = None

    @staticmethod
    @Log(client_log)
    def get_name():
        name = ""
        while not name:
            name = input('Введите имя пользователя: ')
        return name

    @Log(client_log)
    def connect(self, address: str, port: int) -> None:
        """Подключение к серверу"""
        try:
            self.client.connect((address, port))  # подключение
        except Exception as err:
            client_log.error(f"Неудалось установить соединение с вервером {address}:{port}")
            client_log.exception(err)
        else:
            self.con = True
            client_log.info(f"Установлено соединение с сервером {address}:{port}.")

    @Log(client_log)
    def disconnect(self) -> None:
        """отключение от сервера"""
        client_log.info("Отключение от сервера.")
        self.client.close()

    @Log(client_log)
    def __receive_msg(self) -> bytes:
        """Прием ответного сообщения"""
        return self.client.recv(1000000)

    @staticmethod
    @Log(client_log)
    def __validate_response(data):
        """Валидация ответного сообщения от сервера"""
        try:
            data = data.decode('utf-8')
        except Exception as err:
            client_log.error("Принято сообщение не валидного формата.")
            client_log.exception(err)
            return "Message not JSON format."
        else:
            return str(data)

    @Log(client_log)
    def send_message(self, mess: dict) -> str or None:
        """Отправка сообщения серверу"""
        if self.con:
            self.client.send(dumps(mess).encode('utf-8'))
            client_log.info(f"Отправлено сообщение: '{mess}'.")
            if mess['action'] in ("presence", 'message'):
                return None
            response_data = self.__receive_msg()
            response_msg = self.__validate_response(response_data)
            client_log.info(f"Получено сообщение: '{response_msg}'.")
            return response_msg
        else:
            client_log.warning(f"Отправка сообщения невозможна, соединение с сервером небыло установленно.")
            return "Нет активного соединения."

    def create_presence(self):
        out = {
            "action": "presence",
            'time': int(time()),
            'user': {
                'account_name': self.name
            }
        }
        client_log.info(f'Сформировано presence сообщение для пользователя {self.name}')

        return out

    def message_from_server(self):
        while self.run_flag:
            sleep(0.1)
            mes = self.__receive_msg()
            print(self.__validate_response(mes))

    @staticmethod
    def print_help():
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    def create_message(self):
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            'action': 'message',
            'from': self.name,
            'to': to_user,
            'time': int(time()),
            'mess_text': message
        }
        client_log.info(f'Сформирован словарь сообщения: {message_dict}')
        try:
            self.send_message(message_dict)
            client_log.info(f'Отправлено сообщение для пользователя {to_user}')
        except Exception as err:
            client_log.exception(err)
            sys.exit(1)

    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            'action': 'exit',
            'time': int(time()),
            'account_name': self.name
        }

    def user_interactive(self, ):
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                self.send_message(self.create_exit_message())
                print('Завершение соединения.')
                client_log.info('Завершение работы по команде пользователя.')
                self.run_flag = False
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    @Log(client_log)
    def run(self):
        self.connect(self.addr, self.port)
        self.run_flag = True
        while self.run_flag:
            try:
                presence_msg = self.create_presence()
                self.send_message(presence_msg)
            except Exception as err:
                client_log.exception(err)
            else:
                receiver = threading.Thread(target=self.message_from_server)
                receiver.daemon = True
                receiver.start()
                user_interface = threading.Thread(target=self.user_interactive)
                user_interface.daemon = True
                user_interface.start()
                client_log.info('Запущены процессы')
                while True:
                    sleep(0.01)
                    if receiver.is_alive() and user_interface.is_alive():
                        continue
                    print("Выход из клиентской программы.")
                    self.run_flag = False
                    break


if __name__ == "__main__":
    my_client = CustomClient(AF_INET, SOCK_STREAM)
    my_client.run()
