from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from db.connection import get_connection

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.setWindowTitle("로그인")

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("아이디", self.username)
        form.addRow("비밀번호", self.password)

        btn = QPushButton("로그인")
        btn.clicked.connect(self.try_login)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(btn)
        self.setLayout(layout)

    def try_login(self):
        uid = self.username.text().strip()
        pw = self.password.text().strip()

        sql = "SELECT COUNT(*) FROM users WHERE username=%s AND password=%s"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (uid, pw))
                count, = cur.fetchone()

        if count == 1:
            self.accept()
        else:
            QMessageBox.warning(self, "실패", "아이디 또는 비밀번호 오류")