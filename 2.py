"""
Написать функцию host_range_ping()
для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""
import platform
import subprocess
import os


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


def host_range_ping(subnet: str, start: int, stop: int):
    """
    Проверка доступности хостов в указанной подсети в указанном диапазоне
    :param subnet: подсеть
    :param start: начальный ip адресс диапазона
    :param stop: конечный ip адресс диапазона
    :return: результат работы функции вывод доступности хостов
    """
    for i in range(start, stop + 1):
        host = f"{subnet}.{i}"
        if ping(host):
            print(f"Host {host} is available")
        else:
            print(f"Host {host} is not available")


if __name__ == "__main__":
    host_range_ping('192.168.203', 1, 10)
