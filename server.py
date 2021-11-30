from socket import socket, AF_INET, SOCK_STREAM
from socket import timeout as TimeoutError
from select import select
import argparse
from json import dumps, loads

from log_conf.server_log_config import server_log
from decos import Log

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

    def __get__(self, instance, instance_type):
        return self._value

    def __set__(self, instance, value):
        if not (isinstance(value, int) and value > 0):
            raise ValueError(f"Invalid Port {value}")
        self._value = value


class IncorrectDataRecivedError(Exception):
    """Исключение  - некорректные данные получены от сокета"""

    def __str__(self):
        return 'Принято некорректное сообщение от удалённого компьютера.'


class NonDictInputError(Exception):
    """Исключение - аргумент функции не словарь"""

    def __str__(self):
        return 'Аргумент функции должен быть словарём.'


class ServerVerifier(type):

    def __init__(cls, class_name, bases, class_dict):
        for key in class_dict:
            if key == "connect":
                raise ValueError(f"Вызов {key} не в положенном месте")
        type.__init__(cls, class_name, bases, class_dict)


class CustomServer(metaclass=ServerVerifier):
    """Кастомный сервер"""
    port = ValidPort()

    def __init__(self, family: int, type_: int, interval: int, addr: str, port: int, max_clients: int) -> None:
        self.port = port
        self.server = socket(family, type_)
        self.server.settimeout(interval)
        self.server.bind((addr, self.port))
        self.server.listen(max_clients)

    @staticmethod
    def send_message(sock, message):
        if not isinstance(message, dict):
            raise NonDictInputError
        js_message = dumps(message)
        encoded_message = js_message.encode('utf-8')
        sock.send(encoded_message)

    def process_client_message(self, message, messages_list, client, clients, names):
        server_log.info(f'Разбор сообщения от клиента : {message}')
        if 'action' in message and message['action'] == 'presence' and \
                'time' in message and 'user' in message:
            if message['user']['account_name'] not in names.keys():
                names[message['user']['account_name']] = client
                self.send_message(client, {'response': 200})
            else:
                response = {'response': 400, 'error': None}
                response['error'] = 'Имя пользователя уже занято.'
                self.send_message(client, response)
                clients.remove(client)
                client.close()
            return
        elif 'action' in message and message['action'] == 'message' and \
                'to' in message and 'time' in message \
                and 'from' in message and 'mess_text' in message:
            messages_list.append(message)
            return
        elif 'action' in message and message['action'] == 'exit' and 'account_name' in message:
            clients.remove(names[message['account_name']])
            names[message['account_name']].close()
            del names[message['account_name']]
            return
        else:
            response = {'response': 400, 'error': None}
            response['error'] = 'Запрос некорректен.'
            self.send_message(client, response)
            return

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

    def process_message(self, message, names, listen_socks):
        if message['to'] in names and names[message['to']] in listen_socks:
            self.send_message(names[message['to']], message)
            server_log.info(f'Отправлено сообщение пользователю {message["to"]} от пользователя {message["from"]}.')
        elif message['to'] in names and names[message['to']] not in listen_socks:
            raise ConnectionError
        else:
            server_log.error(
                f'Пользователь {message["to"]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    @Log(server_log)
    def run(self) -> None:
        """Запуск сервера"""
        server_log.warning("Запуск сервера")
        clients = []
        recv_data_lst = []
        send_data_lst = []
        messages = []
        names = dict()
        while True:
            try:
                client, address = self.server.accept()  # ловим подключение
                server_log.info(f"Установлено соединение с клиентом: {address}.")
            except TimeoutError:
                pass
                # server_log.info("Клиентов не обнаружено")
            else:
                clients.append(client)
            finally:
                try:
                    if clients:
                        recv_data_lst, send_data_lst, err_lst = select(clients, clients, [], 0)
                except Exception as err:
                    server_log.exception(err)
                else:
                    # принимаем сообщения и если ошибка, исключаем клиента.
                    # print(recv_data_lst)
                    if recv_data_lst:
                        for client_with_message in recv_data_lst:
                            try:
                                self.process_client_message(self.get_message(client_with_message),
                                                            messages, client_with_message, clients, names)
                            except Exception:
                                server_log.info(f'Клиент {client_with_message.getpeername()} '
                                                f'отключился от сервера.')
                                self.clients.remove(client_with_message)

                    # Если есть сообщения, обрабатываем каждое.
                    for i in messages:
                        try:
                            self.process_message(i, names, send_data_lst)
                        except Exception:
                            server_log.info(f'Связь с клиентом с именем {i["to"]} была потеряна')
                            clients.remove(names[i["to"]])
                            del names[i["to"]]
                    messages.clear()


if __name__ == "__main__":
    my_serv = CustomServer(family=AF_INET,
                           type_=SOCK_STREAM,
                           interval=0.5,
                           addr=args.addr,
                           port=args.port,
                           max_clients=5)
    my_serv.run()
