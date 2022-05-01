"""Тестирование сервера
p.s. устарело и не обновлялось.
"""
from multiprocessing import Process
from multiprocessing import set_start_method
from time import time
from socket import AF_INET, SOCK_STREAM
from unittest import TestCase, main

from client_dist.client.client import CustomClient
from .server import CustomServer


class TestClientServerApplication(TestCase):
    """Тестовое клиент-серверное приложение"""
    def setUp(self):
        # предварительная настройка
        self.test_client = CustomClient(AF_INET, SOCK_STREAM, 10)
        self.test_client.connect("localhost", 8888)

    def tearDown(self):
        # завершающие действия
        self.test_client.disconnect()

    def test_presence(self):
        self.assertEqual(self.test_client.send_message({
            "action": "presence",
            "time": int(time()),
            "type": "status",
            "user": {
                "account_name": "Klark Charlz",
                "status": "Online"
            }
        }), "{'alert': 'OK', 'response': 200}")

    def test_unknown_action(self):
        self.assertEqual(self.test_client.send_message({
            "action": "presdence",
            "time": int(time()),
            "type": "status",
            "user": {
                "account_name": "Klark Charlz",
                "status": "Online"
            }}),
            "{'error': 'Поле action содержит не допустимое значение.', 'response': 400}")

    def test_not_action(self):
        self.assertEqual(self.test_client.send_message({
            "actiion": "presence",
            "time": int(time()),
            "type": "status",
            "user": {
                "account_name": "Klark Charlz",
                "status": "Online"
            }}),
            "{'error': 'Отсутствует поле action.', 'response': 400}")

    def test_not_time(self):
        self.assertEqual(self.test_client.send_message({
            "action": "presence",
            "timde": int(time()),
            "type": "status",
            "user": {
                "account_name": "Klark Charlz",
                "status": "Online"
            }}),
            "{'error': 'Отсутствует поле time.', 'response': 400}")

    def test_invalid_time(self):
        self.assertEqual(self.test_client.send_message({
            "action": "presence",
            "time": "int(time())",
            "type": "status",
            "user": {
                "account_name": "Klark Charlz",
                "status": "Online"
            }
        }), "{'error': 'Поле time не валидного значения', 'response': 400}")


if __name__ == "__main__":
    # запустим тестовый сервер
    set_start_method("fork")  # иначе на маке не запускаются процессы
    test_serv = CustomServer(family=AF_INET,
                             type_=SOCK_STREAM,
                             interval=10,
                             addr='',
                             port=8888,
                             max_clients=5)
    server_run = Process(target=test_serv.run, daemon=True)
    server_run.start()

    main()
