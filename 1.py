"""
Написать функцию host_ping(),
в которой с помощью утилиты ping будет проверяться доступность сетевых узлов.
Аргументом функции является список,
в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять их доступность
с выводом соответствующего сообщения («Узел доступен», «Узел недоступен»).
При этом ip-адрес сетевого узла должен создаваться с помощью функции ip_address().
"""
import platform
import subprocess
import os


HOSTS = ['192.168.203.25', '192.168.203.30', '192.168.203.1', '192.168.203.8']


def ping(host: str) -> bool:
    """
    вызов команды пинг с указанным хостом
    :param host: хост
    :return: true - хост доступен, false - нет
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    return subprocess.call(command, stdout=devnull, stderr=subprocess.STDOUT) == 0


def availability_host(hosts_list: list) -> None:
    """
    Проверка доступности хостов
    :param hosts_list: список хостов
    :return: результат работы функции вывод доступности хостов
    """
    for host in hosts_list:
        if ping(host):
            print(f"Host {host} is available")
        else:
            print(f"Host {host} is not available")


if __name__ == "__main__":
    availability_host(HOSTS)
