from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
from db.item_repository import ItemRepository
from views.insert_dialog import InsertDialog
from views.update_dialog import UpdateDialog
from views.delete_dialog import DeleteDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Samsung")
        self.resize(950, 550)

        self.repo = ItemRepository()

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 상단 통합 바
        top_layout = QHBoxLayout()

        label = QLabel("검색")
        label.setFixedWidth(40)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("상품명 또는 코드 검색...")
        self.search_input.setFixedWidth(300)
        self.search_input.setFixedHeight(28)
        self.search_input.textChanged.connect(self.load_items)

        self.btn_insert = QPushButton("추가")
        self.btn_update = QPushButton("수정")
        self.btn_delete = QPushButton("삭제")

        self.btn_insert.setFixedWidth(80)
        self.btn_update.setFixedWidth(80)
        self.btn_delete.setFixedWidth(80)

        self.btn_insert.clicked.connect(self.open_insert)
        self.btn_update.clicked.connect(self.open_update)
        self.btn_delete.clicked.connect(self.open_delete)

        top_layout.addWidget(label)
        top_layout.addWidget(self.search_input)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_insert)
        top_layout.addWidget(self.btn_update)
        top_layout.addWidget(self.btn_delete)

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "코드", "상품명", "가격", "재고"])

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)

        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # 스타일
        self.setStyleSheet("""
            QMainWindow {
                background-color: #e9e9e9;
            }

            QPushButton {
                background-color: #d0d0d0;
                color: black;
                padding: 5px 12px;
                border: 1px solid #a0a0a0;
                border-radius: 0px;
            }

            QPushButton:hover {
                background-color: #c2c2c2;
            }

            QPushButton:pressed {
                background-color: #b0b0b0;
            }

            QTableWidget {
                background-color: white;
                gridline-color: #c8c8c8;
                font-size: 12px;
            }

            QHeaderView::section {
                background-color: #dcdcdc;
                border: 1px solid #b5b5b5;
                font-weight: bold;
                padding: 4px;
            }

            QLineEdit {
                padding: 5px;
                border: 1px solid #b5b5b5;
                background: white;
            }
        """)

        # 레이아웃 적용
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.table)

        self.load_items()

    # 데이터 로드
    def load_items(self):
        keyword = self.search_input.text().strip().lower()
        rows = self.repo.fetch_all()

        if keyword:
            rows = [
                row for row in rows
                if keyword in row[1].lower() or keyword in row[2].lower()
            ]

        # 정렬 완전 비활성화
        self.table.setSortingEnabled(False)

        self.table.clearContents()
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            for c, value in enumerate(row):

                item = QTableWidgetItem()

                # ID 컬럼 숫자 정렬 처리
                if c == 0:
                    numeric_value = int(value)
                    item.setData(Qt.EditRole, numeric_value)

                # 가격 숫자 정렬 처리
                elif c == 3:
                    numeric_value = int(value)
                    item.setData(Qt.EditRole, numeric_value)
                    item.setText(f"{numeric_value:,}")

                else:
                    item.setText(str(value))

                if c in (3, 4):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.table.setItem(r, c, item)

        # 정렬 활성화
        self.table.setSortingEnabled(True)

    # 다이얼로그
    def open_insert(self):
        dialog = InsertDialog()
        if dialog.exec_() == QDialog.Accepted:
            self.load_items()

    def open_update(self):
        row = self.table.currentRow()
        if row < 0:
            return

        item_id = self.table.item(row, 0).text()
        dialog = UpdateDialog(item_id)
        if dialog.exec_() == QDialog.Accepted:
            self.load_items()

    def open_delete(self):
        row = self.table.currentRow()
        if row < 0:
            return

        item_id = self.table.item(row, 0).text()
        dialog = DeleteDialog(item_id)
        if dialog.exec_() == QDialog.Accepted:
            self.load_items()