"""Удаление контакта"""

from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QPushButton
from PyQt5.QtCore import Qt

from server_dist.log_conf.client_log_config import client_log
from server_dist.database.function import get_client_contacts

logger = client_log


class DelContactDialog(QDialog):
    """
        Диалог удаления контакта. Предлагает текущий список контактов,
        не имеет обработчиков для действий.
        """

    def __init__(self, transport):
        super().__init__()
        self.transport = transport

        self.setFixedSize(350, 120)
        self.setWindowTitle('Выберите контакт для удаления:')

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setModal(True)

        self.selector_label = QLabel('Выберите контакт для удаления:', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.selector.addItems(sorted(get_client_contacts(self.transport.session)))

        self.btn_ok = QPushButton('Удалить', self)
        self.btn_ok.setFixedSize(100, 30)
        self.btn_ok.move(230, 20)

        self.btn_cancel = QPushButton('Отмена', self)
        self.btn_cancel.setFixedSize(100, 30)
        self.btn_cancel.move(230, 60)
        self.btn_cancel.clicked.connect(self.close)
