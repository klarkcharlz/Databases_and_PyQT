from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from socket import timeout as TimeoutError
from select import select
import argparse
from json import dumps, loads
import dis
import threading

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow

from log_conf.server_log_config import server_log
from decos import Log
from database.function import connect as connect_db
from database.function import (user_logout,
                               user_login,
                               process_message,
                               get_contacts,
                               add_contact,
                               remove_contact,
                               users_list)

TIMEOUT = 0.5

new_connection = False
conflag_lock = threading.Lock()

parser = argparse.ArgumentParser(description='JSON instant messaging client.')
parser.add_argument(
    '-addr',
    type=str,
    default='',
    help='Server IP (default: '')'
)
parser.add_argument(
    '-port',
    type=int,
    default=7777,
    help='Server IP (default: 7777)'
)
args = parser.parse_args()


class ValidPort:
    """
    Это должно быть целое число (>=0). Значение порта по умолчанию равняется 7777.
    """
    def __get__(self, instance, instance_type):
        return instance.__dict__[self.value]

    def __set__(self, instance, value=7777):
        if not isinstance(value, int):
            if value <= 0:
                raise ValueError(f"Invalid Port {value}")
        instance.__dict__[self.value] = value

    def __set_name__(self, owner, name):
        self.value = name


class IncorrectDataRecivedError(Exception):
    """Исключение  - некорректные данные получены от сокета"""

    def __str__(self):
        return 'Принято некорректное сообщение от удалённого компьютера.'


class NonDictInputError(Exception):
    """Исключение - аргумент функции не словарь"""

    def __str__(self):
        return 'Аргумент функции должен быть словарём.'


class ServerVerifier(type):
    """
    отсутствие вызовов connect для сокетов;
    использование сокетов для работы по TCP.
    """

    def __init__(cls, class_name, bases, class_dict):
        methods = []
        methods_2 = []
        attrs = []
        for func in class_dict:
            try:
                ret = dis.get_instructions(class_dict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_METHOD':
                        if i.argval not in methods_2:
                            methods_2.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        if 'connect' in methods:
            raise TypeError('Использование метода connect недопустимо в серверном классе')
        # ToDo при моей инициализации не отображает эти переменные, переделать инициализацию ?
        # if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
        #     raise TypeError('Некорректная инициализация сокета.')

        super().__init__(class_name, bases, class_dict)


class CustomServer(threading.Thread, metaclass=ServerVerifier):
    port = ValidPort()

    def __init__(self, family: int, type_: int, interval: int or float, addr: str, port: int, max_clients: int) -> None:
        super().__init__()
        self.port = port
        self.family = family
        self.type_ = type_
        self.interval = interval
        self.addr = addr
        self.max_clients = max_clients

        self.server = None
        self.session = connect_db("./db/server.db3")

        self.clients = []
        self.messages = []
        self.names = dict()

    def init_sock(self):
        self.server = socket(self.family, self.type_)
        self.server.settimeout(self.interval)
        self.server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server.bind((self.addr, self.port))
        self.server.listen(self.max_clients)

    def process_client_message(self, message, client):
        global new_connection
        server_log.info(f'Разбор сообщения от клиента : {message}')
        # presence
        if 'action' in message and message['action'] == 'presence' and \
                'time' in message and 'user' in message:
            if message['user']['account_name'] not in self.names.keys():
                self.names[message['user']['account_name']] = client
                client_ip, client_port = client.getpeername()
                user_login(self.session, message['user']['account_name'], client_ip, client_port)
                self.send_message(client, {'response': 200})
                with conflag_lock:
                    new_connection = True
            else:
                response = {'response': 400, 'error': 'Имя пользователя уже занято.'}
                self.send_message(client, response)
                self.clients.remove(client)
                client.close()
        # message
        elif 'action' in message and message['action'] == 'message' and \
                'to' in message and 'time' in message \
                and 'from' in message and 'mess_text' in message:
            self.messages.append(message)
            process_message(self.session, message['from'], message['to'])
        # exit
        elif 'action' in message and message['action'] == 'exit' and 'account_name' in message:
            user_logout(self.session, message['account_name'])
            self.clients.remove(self.names[message['account_name']])
            self.names[message['account_name']].close()
            del self.names[message['account_name']]
            with conflag_lock:
                new_connection = True
        # get_contacts
        elif 'action' in message and message['action'] == 'get_contacts' and 'user' in message and \
                self.names[message['user']] == client:
            response = {'response': 202,
                        'data_list': get_contacts(self.session, message['user'])}
            self.send_message(client, response)
        # add
        elif 'action' in message and message['action'] == 'add' and 'account_name' in message and 'user' in message \
                and self.names[message['user']] == client:
            add_contact(self.session, message['user'], message['account_name'])
            self.send_message(client, {'response': 200})
        # remove
        elif 'action' in message and message['action'] == 'remove' and 'account_name' in message and 'user' in message \
                and self.names[message['user']] == client:
            remove_contact(self.session, message['user'], message['account_name'])
            self.send_message(client, {'response': 200})
        # Если это запрос известных пользователей
        elif 'action' in message and message['action'] == 'get_users' and 'account_name' in message \
                and self.names[message['account_name']] == client:
            response = {'response': 202,
                        'data_list': [user[0] for user in users_list(self.session)]
                        }
            self.send_message(client, response)
        else:
            response = {'response': 400, 'error': 'Запрос некорректен.'}
            self.send_message(client, response)

    @staticmethod
    def get_message(client):
        encoded_response = client.recv(1024)
        if isinstance(encoded_response, bytes):
            json_response = encoded_response.decode('utf-8')
            response = loads(json_response)
            if isinstance(response, dict):
                return response
            else:
                raise IncorrectDataRecivedError
        else:
            raise IncorrectDataRecivedError

    @staticmethod
    def send_message(sock, message):
        if not isinstance(message, dict):
            raise NonDictInputError
        js_message = dumps(message)
        encoded_message = js_message.encode('utf-8')
        sock.send(encoded_message)

    def process_message(self, message, listen_socks):
        if message['to'] in self.names and self.names[message['to']] in listen_socks:
            self.send_message(self.names[message['to']], message)
            server_log.info(f'Отправлено сообщение пользователю {message["to"]} от пользователя {message["from"]}.')
        elif message['to'] in self.names and self.names[message['to']] not in listen_socks:
            raise ConnectionError
        else:
            server_log.error(
                f'Пользователь {message["to"]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    @Log(server_log)
    def run(self) -> None:
        """Запуск сервера"""
        self.init_sock()

        server_log.warning("Запуск сервера")

        while True:
            try:
                client, address = self.server.accept()  # ловим подключение
                server_log.info(f"Установлено соединение с клиентом: {address}.")
            except TimeoutError:
                pass
                # server_log.info("Клиентов не обнаружено")
            else:
                server_log.info(f'Установлено соедение с ПК {address}')
                self.clients.append(client)
            finally:
                recv_data_lst = []
                send_data_lst = []
                try:
                    # print(clients)
                    # print(recv_data_lst)
                    # print(send_data_lst)
                    if self.clients:
                        recv_data_lst, send_data_lst, err_lst = select(self.clients, self.clients, [], 0)
                except Exception as err:
                    server_log.exception(err)
                else:
                    # принимаем сообщения и если ошибка, исключаем клиента.
                    # print(recv_data_lst)
                    if recv_data_lst and self.clients:
                        for client_with_message in recv_data_lst:
                            try:
                                self.process_client_message(self.get_message(client_with_message), client_with_message)
                            except:
                                server_log.info(f'Клиент {client_with_message.getpeername()} '
                                                f'отключился от сервера.')
                                for name in self.names:
                                    if self.names[name] == client_with_message:
                                        user_logout(self.session, name)
                                        del self.names[name]
                                        break
                                self.clients.remove(client_with_message)

                    # Если есть сообщения, обрабатываем каждое.
                    for message in self.messages:
                        try:
                            self.process_message(message, send_data_lst)
                        except:
                            server_log.info(f'Связь с клиентом с именем {message["to"]} была потеряна')
                            self.clients.remove(self.names[message["to"]])
                            user_logout(message["to"])
                            del self.names[message["to"]]
                    self.messages.clear()


def main():
    my_serv = CustomServer(family=AF_INET,
                           type_=SOCK_STREAM,
                           interval=TIMEOUT,
                           addr=args.addr,
                           port=args.port,
                           max_clients=5)
    my_serv.daemon = True
    my_serv.start()


if __name__ == "__main__":
    main()
    from time import sleep
    while True:
        sleep(1)
