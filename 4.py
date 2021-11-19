"""
Продолжаем работать над проектом «Мессенджер»:
Реализовать скрипт, запускающий два клиентских приложения:
на чтение чата и на запись в него. Уместно использовать модуль subprocess);
Реализовать скрипт, запускающий указанное количество клиентских приложений.
"""
import os
import subprocess
import sys
from time import sleep

PYTHON_PATH = sys.executable
BASE_PATH = os.path.dirname(os.path.abspath(__file__))


def get_subprocess(file_with_args):
    sleep(0.2)
    file_full_path = f"{PYTHON_PATH} {BASE_PATH}/{file_with_args}"
    args = ["gnome-terminal", "--disable-factory", "--", "bash", "-c", file_full_path]
    return subprocess.Popen(args, preexec_fn=os.setpgrp)


process = []
for type_ in ("sender", "reader"):
    process.append(get_subprocess(f"client.py. -type test{type_}"))
