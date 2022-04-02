"""
Написать функцию host_range_ping_tab(),
возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам,
представленным в табличном формате (использовать модуль tabulate).
Таблица должна состоять из двух колонок.
"""
import platform
import subprocess
import os
from tabulate import tabulate
from collections import defaultdict


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


def host_range_ping(subnet: str, start: int, stop: int) -> dict:
    """
    Проверка доступности хостов в указанной подсети в указанном диапазоне
    :param subnet: подсеть
    :param start: начальный ip адресс диапазона
    :param stop: конечный ip адресс диапазона
    :return: {хост: доступен/недоступен}
    """
    ping_result = {}
    for i in range(start, stop + 1):
        host = f"{subnet}.{i}"
        if ping(host):
            ping_result[host] = True
        else:
            ping_result[host] = False
    return ping_result


def print_table(data: dict) -> None:
    """
    Печать таблицы доступности хостов
    :param data: словарь с результатми пинга хостов
    :return: результат работы функции таблица с колонкой доступны и колонкой недоступных хостов
    """
    lists_dict = defaultdict(list)
    for host, ping_ in data.items():
        if ping_:
            lists_dict['Reachable'].append(host)
        else:
            lists_dict['Unreachable'].append(host)
    print(tabulate(lists_dict, headers='keys'))


if __name__ == "__main__":
    result = host_range_ping('192.168.203', 1, 10)
    print_table(result)
