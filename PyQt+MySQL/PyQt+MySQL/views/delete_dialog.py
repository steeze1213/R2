from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from db.item_repository import ItemRepository


class DeleteDialog(QDialog):
    def __init__(self, item_id):
        super().__init__()

        self.setWindowTitle("상품 삭제")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.repo = ItemRepository()
        self.item_id = item_id

        # 안내 문구
        label = QLabel("정말 삭제하시겠습니까?")
        label.setAlignment(Qt.AlignCenter)

        # 버튼
        self.btn_ok = QPushButton("삭제")
        self.btn_cancel = QPushButton("취소")

        self.btn_ok.setFixedWidth(80)
        self.btn_cancel.setFixedWidth(80)

        self.btn_ok.clicked.connect(self.delete_item)
        self.btn_cancel.clicked.connect(self.reject)

        # 버튼 레이아웃
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        # 메인 레이아웃
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.addWidget(label)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def delete_item(self):
        self.repo.delete(self.item_id)
        QMessageBox.information(self, "완료", "삭제되었습니다.")
        self.accept()