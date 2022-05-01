"""Главный класс клиентского приложения"""

from socket import socket, AF_INET, SOCK_STREAM
import argparse
from time import time, sleep
from json import dumps, loads
import sys
import dis
import threading
import json
import os
import hashlib
import binascii
import hmac

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, QObject
from Cryptodome.PublicKey import RSA

sys.path.append('../../')

from server_dist.log_conf.client_log_config import client_log
from server_dist.decos import Log
from server_dist.database.function import get_client_session as connect_db
from server_dist.database.function import add_users, add_client_contact, save_message

from .client_gui import ClientMainWindow
from .start_dialog import UserNameDialog
from .errors import ServerError

socket_lock = threading.Lock()

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
parser.add_argument(
    '-name',
    type=str,
    default="",
    help='Username'
)

parser.add_argument(
    '-pas',
    type=str,
    default="",
    help='Password'
)

args = parser.parse_args()

sock_lock = threading.Lock()
database_lock = threading.Lock()


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


class CustomClient(threading.Thread, QObject):
    """Клиентский класс"""
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()
    message_205 = pyqtSignal()

    def __init__(self, family: int, type_: int, keys, timeout_=None) -> None:
        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.client = socket(family, type_)
        if timeout_:
            self.client.settimeout(timeout_)
        self.con = False
        self.addr = args.addr
        self.port = args.port
        self.name = args.name
        self.password = args.pas
        self.run_flag = None
        self.keys = keys
        self.session = connect_db(self.name)
        self.connect(self.addr, self.port)

        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                client_log.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            client_log.error(
                'Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            client_log.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')

        self.passwd_hash_string = None
        self.pubkey = None
        self.need_key = None

    def add_contact(self, contact):
        """Добавление контакта"""
        client_log.debug(f'Создание контакта {contact}')
        req = {
            'action': 'add',
            'time': int(time()),
            'user': self.name,
            'account_name': contact
        }
        with socket_lock:
            self.send_message(req)

    def remove_contact(self, contact):
        """Удаление контакта"""
        client_log.debug(f'Удаление контакта {contact}')
        req = {
            'action': 'remove',
            'time': int(time()),
            'user': self.name,
            'account_name': contact
        }
        with socket_lock:
            self.send_message(req)

    def user_list_update(self):
        """Обновление списка пользователей"""
        get_users_msg = self.create_get_users_msg()
        with socket_lock:
            self.send_message(get_users_msg)
            sleep(0.5)
        sleep(0.5)

    def contacts_list_update(self):
        """Обновление списка контактов"""
        get_contacts_msg = self.create_get_contacts_msg()
        with socket_lock:
            self.send_message(get_contacts_msg)
            sleep(0.5)
        sleep(0.5)

    def create_message(self, to, message):
        """Создание сообщения"""
        message_dict = {
            'action': 'message',
            'from': self.name,
            'to': to,
            'time': int(time()),
            'mess_text': message
        }
        client_log.info(f'Сформирован словарь сообщения: {message_dict}')
        try:
            with socket_lock:
                self.send_message(message_dict)
            client_log.info(f'Отправлено сообщение для пользователя {to}')
        except Exception as err:
            client_log.exception(err)
            sys.exit(1)

    @Log(client_log)
    def connect(self, address: str, port: int) -> None:
        """Подключение к серверу"""
        try:
            self.client.connect((address, port))  # подключение
        except Exception as err:
            client_log.error(f"Неудалось установить соединение с вервером {address}:{port}")
            client_log.exception(err)
            raise ServerError('Не удалось установить соединение с сервером')
        else:
            passwd_bytes = self.password.encode('utf-8')
            salt = self.username.lower().encode('utf-8')
            passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
            self.passwd_hash_string = binascii.hexlify(passwd_hash)
            self.pubkey = self.keys.publickey().export_key().decode('ascii')

            self.con = True
            self.run_flag = True
            client_log.info(f"Установлено соединение с сервером {address}:{port}.")
            with socket_lock:
                presence_msg = self.create_presence()
                self.send_message(presence_msg)
                sleep(0.5)
            sleep(0.5)

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
    def send_message(self, mess: dict) -> None or dict:
        """Отправка сообщения серверу"""
        if self.con:
            self.client.send(dumps(mess).encode('utf-8'))
            client_log.info(f"Отправлено сообщение: '{mess}'.")
            if mess['action'] in ('message', 'exit'):
                return
            response_data = self.__receive_msg()
            response_msg = self.__validate_response(response_data)
            client_log.info(f"Получено сообщение: '{response_msg}'.")
            if mess['action'] == 'pubkey_need':
                return response_msg
            self.parse_response(loads(response_msg))
        else:
            client_log.warning(f"Отправка сообщения невозможна, соединение с сервером небыло установленно.")

    def create_presence(self):
        """Создание presence сообщения"""
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
        """Разбор ответа от сервера"""
        if 'response' in response and response['response'] == 202:
            data_list = response['data_list']
            if response['type'] == 'get_users':
                client_log.info("Принят список пользователей.")
                add_users(self.session, data_list)
            elif response['type'] == 'get_contacts':
                client_log.info("Принят список контактов.")
                for contact in data_list:
                    add_client_contact(self.session, contact)

        elif response['response'] == 205:
            self.user_list_update()
            self.contacts_list_update()
            self.message_205.emit()

        elif response['response'] == 400:
            raise ServerError(f'{response["error"]}')

        elif 'action' in response \
                and response['action'] == 'message' \
                and 'from' in response \
                and 'to' in response \
                and 'mess_text' in response \
                and response['to'] == self.name:
            client_log.debug(f'Получено сообщение от пользователя {response["from"]}:'
                             f'{response["mess_text"]}')
            save_message(self.session, response['from'], 'in', response['mess_text'])
            self.new_message.emit(response['from'])

        elif response['response'] == 400:
            raise ServerError(response['error'])

        elif response['response'] == 511:
            ans_data = response['bin']
            hash = hmac.new(self.passwd_hash_string, ans_data.encode('utf-8'), 'MD5')
            digest = hash.digest()
            my_ans = {'response': 511, 'bin': binascii.b2a_base64(
                digest).decode('ascii')}
            self.send_message(self.transport, my_ans)

    def key_request(self, user):
        """Запрос ключей"""
        client_log.debug(f'Запрос публичного ключа для {user}')
        req = {
            'action': 'pubkey_need',
            'time': int(time()),
            'account_name': user
        }
        with socket_lock:
            data = self.send_message(req)
            if data:
                return data
            else:
                client_log.error(f'Не удалось получить ключ собеседника{user}.')

    def message_from_server(self):
        """Ожидание сообщение от сервера"""
        mes = self.__receive_msg()
        mes = loads(self.__validate_response(mes))
        self.parse_response(mes)

    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            'action': 'exit',
            'time': int(time()),
            'account_name': self.name
        }

    def shutdown(self):
        """Отключение клиента"""
        with socket_lock:
            self.send_message(self.create_exit_message())
            sleep(0.5)
        print('Завершение соединения.')
        client_log.info('Завершение работы по команде пользователя.')
        self.disconnect()
        self.run_flag = False
        sleep(0.5)

    def create_get_users_msg(self):
        """Создание сообщения на запрос пользователей"""
        client_log.info(f'Запрос списка известных пользователей {self.name}')
        return {
            'action': 'get_users',
            'time': int(time()),
            'account_name': self.name
        }

    def create_get_contacts_msg(self):
        """Создание сообщения на запрос контактов"""
        client_log.info(f'Запрос контакт листа для пользователя {self.name}')
        return {
            'action': 'get_contacts',
            'time': int(time()),
            'user': self.name
        }

    @Log(client_log)
    def run(self):
        """Запуск клиента"""
        while self.run_flag:
            sleep(1)
            with socket_lock:
                try:
                    self.client.settimeout(0.5)
                    self.message_from_server()
                except OSError as err:
                    if err.errno:
                        client_log.critical(f'Потеряно соединение с сервером.')
                        self.run_flag = False
                        self.connection_lost.emit()
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    client_log.debug(f'Потеряно соединение с сервером.')
                    self.run_flag = False
                    self.connection_lost.emit()
                else:
                    pass
                finally:
                    self.client.settimeout(5)


def main():
    """Основная функция, подготовка и запуск клиентского приложения"""
    client_app = QApplication(sys.argv)

    start_dialog = UserNameDialog()
    if not args.name or not args.pas:

        client_app.exec_()
        if start_dialog.ok_pressed:
            args.name = start_dialog.client_name.text()
            args.pas = start_dialog.client_passwd.text()
        else:
            exit(0)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{args.name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    try:
        my_client = CustomClient(AF_INET, SOCK_STREAM, keys)
        my_client.daemon = True
        my_client.start()
    except ServerError as error:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', error.text)
        exit(1)

    del start_dialog

    main_window = ClientMainWindow(my_client, keys)
    main_window.make_connection(my_client)
    main_window.setWindowTitle(f'Чат Программа alpha release - {my_client.name}')
    client_app.exec_()

    my_client.shutdown()
    my_client.join()


if __name__ == "__main__":
    main()
