from socket import socket, AF_INET, SOCK_STREAM
from socket import timeout as TimeoutError
from select import select
import argparse
from json import dumps, loads
import dis

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


class CustomServer(metaclass=ServerVerifier):
    port = ValidPort()

    def __init__(self, family: int, type_: int, interval: int or float, addr: str, port: int, max_clients: int) -> None:
        self.port = port
        self.server = socket(family, type_)
        self.server.settimeout(interval)
        self.server.bind((addr, self.port))
        self.server.listen(max_clients)

    def process_client_message(self, message, messages_list, client, clients, names):
        server_log.info(f'Разбор сообщения от клиента : {message}')
        if 'action' in message and message['action'] == 'presence' and \
                'time' in message and 'user' in message:
            if message['user']['account_name'] not in names.keys():
                names[message['user']['account_name']] = client
                self.send_message(client, {'response': 200})
            else:
                response = {'response': 400, 'error': 'Имя пользователя уже занято.'}
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
            response = {'response': 400, 'error': 'Запрос некорректен.'}
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
                recv_data_lst = []
                send_data_lst = []
                try:
                    # print(clients)
                    # print(recv_data_lst)
                    # print(send_data_lst)
                    if clients:
                        recv_data_lst, send_data_lst, err_lst = select(clients, clients, [], 0)
                except Exception as err:
                    server_log.exception(err)
                else:
                    # принимаем сообщения и если ошибка, исключаем клиента.
                    # print(recv_data_lst)
                    if recv_data_lst and clients:
                        for client_with_message in recv_data_lst:
                            try:
                                self.process_client_message(self.get_message(client_with_message),
                                                            messages, client_with_message, clients, names)
                            except:
                                server_log.info(f'Клиент {client_with_message.getpeername()} '
                                                f'отключился от сервера.')
                                clients.remove(client_with_message)

                    # Если есть сообщения, обрабатываем каждое.
                    for i in messages:
                        try:
                            self.process_message(i, names, send_data_lst)
                        except:
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
