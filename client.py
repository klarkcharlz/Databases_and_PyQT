from socket import socket, AF_INET, SOCK_STREAM
import argparse
from time import time, sleep
from json import dumps, loads
import sys
import dis
import threading

from log_conf.client_log_config import client_log
from decos import Log

from database.function import get_client_session as connect_db
from database.function import add_users, add_client_contact


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

sock_lock = threading.Lock()
database_lock = threading.Lock()


class ServerError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


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


class CustomClient(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, family: int, type_: int, timeout_=None) -> None:
        super().__init__()

        self.client = socket(family, type_)
        if timeout_:
            self.client.settimeout(timeout_)
        self.con = False
        self.addr = args.addr
        self.port = args.port
        self.name = self.get_name()
        self.run_flag = None
        self.session = connect_db(self.name)

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
            exit(1)
        else:
            self.con = True
            client_log.info(f"Установлено соединение с сервером {address}:{port}.")

    @Log(client_log)
    def disconnect(self) -> None:
        """отключение от сервера"""
        client_log.info("Отключение от сервера.")
        self.client.close()
        sleep(0.5)

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
            return data

    @Log(client_log)
    def send_message(self, mess: dict) -> None:
        """Отправка сообщения серверу"""
        if self.con:
            self.client.send(dumps(mess).encode('utf-8'))
            client_log.info(f"Отправлено сообщение: '{mess}'.")
            if mess['action'] in ("presence", 'message'):
                return
            response_data = self.__receive_msg()
            response_msg = self.__validate_response(response_data)
            client_log.info(f"Получено сообщение: '{response_msg}'.")
            self.parse_response(loads(response_msg))
        else:
            client_log.warning(f"Отправка сообщения невозможна, соединение с сервером небыло установленно.")

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

    def parse_response(self, response: dict):
        if 'response' in response and response['response'] == 202:
            data_list = response['data_list']
            if response['type'] == 'get_users':
                client_log.info("Принят список пользователей.")
                add_users(self.session, data_list)
            elif response['type'] == 'get_contacts':
                client_log.info("Принят список контактов.")
                for contact in data_list:
                    add_client_contact(self.session, contact)

    def message_from_server(self):
        while self.run_flag:
            sleep(0.1)
            mes = self.__receive_msg()
            mes = loads(self.__validate_response(mes))
            self.parse_response(mes)

    @staticmethod
    def print_help():
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')

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
                self.disconnect()
                self.run_flag = False
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    def create_get_users_msg(self):
        client_log.info(f'Запрос списка известных пользователей {self.name}')
        return {
            'action': 'get_users',
            'time': int(time()),
            'account_name': self.name
        }

    def create_get_contacts_msg(self):
        client_log.info(f'Запрос контакт листа для пользователя {self.name}')
        return {
            'action': 'get_contacts',
            'time': int(time()),
            'user': self.name
        }

    @Log(client_log)
    def run(self):
        self.connect(self.addr, self.port)
        self.run_flag = True

        try:
            presence_msg = self.create_presence()
            self.send_message(presence_msg)
            sleep(0.5)
            get_users_msg = self.create_get_users_msg()
            self.send_message(get_users_msg)
            sleep(0.5)
            get_contacts_msg = self.create_get_contacts_msg()
            self.send_message(get_contacts_msg)
            sleep(0.5)
        except Exception as err:
            client_log.exception(err)
            exit(1)
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


def main():
    my_client = CustomClient(AF_INET, SOCK_STREAM)
    my_client.daemon = True
    my_client.start()

    while True:
        sleep(1)
        if my_client.is_alive():
            continue
        break


if __name__ == "__main__":
    main()
