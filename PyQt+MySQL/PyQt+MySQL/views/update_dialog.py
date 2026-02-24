from PyQt5.QtWidgets import *
from db.item_repository import ItemRepository


class UpdateDialog(QDialog):
    def __init__(self, item_id):
        super().__init__()
        self.setWindowTitle("상품 수정")
        self.repo = ItemRepository()
        self.item_id = item_id

        self.input_code = QLineEdit()
        self.input_name = QLineEdit()
        self.input_price = QLineEdit()
        self.input_stock = QLineEdit()

        form = QFormLayout()
        form.addRow("코드", self.input_code)
        form.addRow("상품명", self.input_name)
        form.addRow("가격", self.input_price)
        form.addRow("재고", self.input_stock)

        self.btn_ok = QPushButton("수정")
        self.btn_cancel = QPushButton("취소")

        self.btn_ok.clicked.connect(self.update_item)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.load_data()

    def load_data(self):
        rows = self.repo.fetch_all()
        for row in rows:
            if str(row[0]) == str(self.item_id):
                self.input_code.setText(row[1])
                self.input_name.setText(row[2])
                self.input_price.setText(str(row[3]))
                self.input_stock.setText(str(row[4]))
                break

    def update_item(self):
        code = self.input_code.text().strip()
        name = self.input_name.text().strip()
        price = self.input_price.text().strip()
        stock = self.input_stock.text().strip()

        if not code or not name:
            QMessageBox.warning(self, "오류", "코드와 상품명은 필수입니다.")
            return

        if not price.isdigit() or not stock.isdigit():
            QMessageBox.warning(self, "오류", "가격과 재고는 숫자만 입력하세요.")
            return

        ok = self.repo.update(
            self.item_id,
            code,
            name,
            int(price),
            int(stock)
        )

        if ok:
            QMessageBox.information(self, "완료", "수정되었습니다.")
            self.accept()
        else:
            QMessageBox.critical(self, "실패", "수정 중 오류 발생")