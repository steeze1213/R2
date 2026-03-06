import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import socket
import threading
import time
import requests

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

UDP_IP   = "192.168.0.133"
UDP_PORT = 5000
ESP_IP   = "192.168.0.52"
ESP_PORT = 80

LEVEL_CODE = {
    "SAFE":   20,
    "MID":    21,
    "CLOSE":  22,
    "DANGER": 23,
}

ENV_CODE = {
    "SAFE":   30,
    "WARN":   31,
    "DANGER": 32,
}

def dist_color(cm: int) -> str:
    if cm > 100:  return "#e0e0e0"
    elif cm > 50: return "#e8b84b"
    elif cm > 20: return "#e07b3a"
    else:         return "#cc3333"

class Signals(QObject):
    sonar_updated = pyqtSignal(dict)
    env_updated   = pyqtSignal(dict)
    btn_received  = pyqtSignal(str)

signals = Signals()

def send_code(code: int, retry: int = 5, interval: float = 1.0):
    url = f"http://{ESP_IP}:{ESP_PORT}/"
    for i in range(retry):
        try:
            r = requests.get(url, params={"code": f"{code:02d}"}, timeout=5.0)
            print(f"[HTTP] code={code} → {r.status_code} {r.text.strip()}")
            return
        except requests.exceptions.RequestException as e:
            print(f"[HTTP] 재시도 {i+1}/{retry} — {e}")
            time.sleep(interval)
    print(f"[HTTP] {retry}번 시도 후 실패")


def udp_listen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"[UDP] 수신 대기중 {UDP_IP}:{UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(2048)
        raw = data.decode(errors="replace").strip()
        print(f"[UDP] {raw}")

        items = raw.split(",")
        if not items:
            continue

        if items[0] == "EVT" and len(items) >= 3 and items[1] == "BTN":
            signals.btn_received.emit(items[2].strip())

        elif items[0] == "B1":
            d = {item.split(":")[0]: item.split(":")[1] for item in items[1:]}
            signals.sonar_updated.emit(d)

        elif items[0] == "B2":
            d = {item.split(":")[0]: item.split(":")[1] for item in items[1:]}
            signals.env_updated.emit(d)

class SensorBar(QWidget):
    def __init__(self, direction: str, orientation: str):
        super().__init__()
        self.orientation = orientation
        layout = QVBoxLayout(self) if orientation == "vertical" else QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.dir_label = QLabel(direction)
        self.dir_label.setAlignment(Qt.AlignCenter)
        self.dir_label.setFont(QFont("Arial", 9))
        self.dir_label.setStyleSheet("color:#888888;")

        self.bar = QLabel()
        self.bar.setStyleSheet("background:#e0e0e0; border-radius:8px;")

        if orientation == "vertical":
            self.bar.setFixedSize(60, 100)
            self.setFixedSize(60, 130)
        else:
            self.bar.setFixedSize(100, 60)
            self.setFixedSize(130, 60)

        layout.addWidget(self.dir_label)
        layout.addWidget(self.bar)

    def update_value(self, cm: int):
        self.bar.setStyleSheet(f"background:{dist_color(cm)}; border-radius:8px;")

class EnvGauge(QWidget):
    def __init__(self, title: str, unit: str, min_val: int, max_val: int, color: str):
        super().__init__()
        self.unit    = unit
        self.min_val = min_val
        self.max_val = max_val

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Arial", 10))
        title_lbl.setStyleSheet("color:#888888;")
        layout.addWidget(title_lbl)

        self.bar = QProgressBar()
        self.bar.setRange(min_val, max_val)
        self.bar.setValue(min_val)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(22)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background: #e0e0e0;
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self.bar)

        self.val_lbl = QLabel("--")
        self.val_lbl.setFont(QFont("Arial", 13, QFont.Bold))
        self.val_lbl.setStyleSheet("color:#333333;")
        layout.addWidget(self.val_lbl)

    def update_value(self, val: int):
        clamped = max(self.min_val, min(self.max_val, val))
        self.bar.setValue(clamped)
        self.val_lbl.setText(f"{val} {self.unit}")

class SonarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_level = "?"

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 0, 0, 0)

        title = QLabel("초음파 센서")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setStyleSheet("color:#555555;")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.bar_f = SensorBar("전방", "vertical")
        self.bar_b = SensorBar("후방", "vertical")
        self.bar_l = SensorBar("좌측", "horizontal")
        self.bar_r = SensorBar("우측", "horizontal")

        self.level_label = QLabel("?")
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.level_label.setFixedSize(100, 80)
        self.level_label.setStyleSheet("background:#e0e0e0; border-radius:10px; color:#333333;")

        grid.addWidget(self.bar_f,       0, 1, Qt.AlignHCenter)
        grid.addWidget(self.bar_l,       1, 0, Qt.AlignVCenter)
        grid.addWidget(self.level_label, 1, 1, Qt.AlignCenter)
        grid.addWidget(self.bar_r,       1, 2, Qt.AlignVCenter)
        grid.addWidget(self.bar_b,       2, 1, Qt.AlignHCenter)
        root.addLayout(grid)

        legend_row = QHBoxLayout()
        for color, text in [("#e0e0e0","안전"),("#e8b84b","중간"),("#e07b3a","가까움"),("#cc3333","위험")]:
            box = QLabel(text)
            box.setAlignment(Qt.AlignCenter)
            box.setFixedSize(68, 22)
            box.setFont(QFont("Arial", 9))
            box.setStyleSheet(f"background:{color}; border-radius:4px; color:#1a1a1a;")
            legend_row.addWidget(box)
        root.addLayout(legend_row)

        self.send_btn = QPushButton("현재 상태 LCD로 보내기")
        self.send_btn.setFixedHeight(44)
        self.send_btn.setFont(QFont("Arial", 12))
        self.send_btn.setStyleSheet("""
            QPushButton { background:#333333; color:white; border-radius:8px; }
            QPushButton:hover   { background:#555555; }
            QPushButton:pressed { background:#111111; }
        """)
        self.send_btn.clicked.connect(self.on_send)
        root.addWidget(self.send_btn)

    def update_sonar(self, data: dict):
        def to_int(k):
            try: return int(data.get(k, 999))
            except: return 999

        self.bar_f.update_value(to_int("F"))
        self.bar_b.update_value(to_int("B"))
        self.bar_l.update_value(to_int("L"))
        self.bar_r.update_value(to_int("R"))
        self.current_level = data.get("LV", "?")
        self.level_label.setText(self.current_level)

    def on_send(self):
        code = LEVEL_CODE.get(self.current_level)
        if code is None:
            print("[전송] 상태 없음")
            return
        print(f"[전송] {self.current_level} → code={code}")
        threading.Thread(target=send_code, args=(code,), daemon=True).start()

class EnvPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_level = "?"

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(0, 0, 0, 0)

        title = QLabel("환경 센서")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setStyleSheet("color:#555555;")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        self.temp  = EnvGauge("🌡 온도",  "°C",  -10, 50,   "#e07b3a")
        self.humi  = EnvGauge("💧 습도",  "%",    0,  100,  "#4a90d9")
        self.light = EnvGauge("☀ 조도",  "lux",  0,  1023, "#e8b84b")
        self.sound = EnvGauge("🔊 소리",  "",     0,  100,  "#9b59b6")

        for gauge in [self.temp, self.humi, self.light, self.sound]:
            root.addWidget(gauge)

        self.level_label = QLabel("?")
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.level_label.setFixedHeight(48)
        self.level_label.setStyleSheet("background:#e0e0e0; border-radius:8px; color:#333333;")
        root.addWidget(self.level_label)

        self.send_btn = QPushButton("현재 상태 LCD로 보내기")
        self.send_btn.setFixedHeight(44)
        self.send_btn.setFont(QFont("Arial", 12))
        self.send_btn.setStyleSheet("""
            QPushButton { background:#333333; color:white; border-radius:8px; }
            QPushButton:hover   { background:#555555; }
            QPushButton:pressed { background:#111111; }
        """)
        self.send_btn.clicked.connect(self.on_send)
        root.addWidget(self.send_btn)

    def update_env(self, data: dict):
        def to_int(k):
            try: return int(data.get(k, 0))
            except: return 0

        self.temp.update_value(to_int("T"))
        self.humi.update_value(to_int("H"))
        self.light.update_value(to_int("L"))
        self.sound.update_value(to_int("S"))
        self.current_level = data.get("LV", "?")
        self.level_label.setText(f"상태: {self.current_level}")

    def on_send(self):
        code = ENV_CODE.get(self.current_level)
        if code is None:
            print("[전송] 상태 없음")
            return
        print(f"[전송] {self.current_level} → code={code}")
        threading.Thread(target=send_code, args=(code,), daemon=True).start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESP 모니터")
        self.setMinimumSize(380, 560)
        self.setStyleSheet("background:#f5f5f5;")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        indicator_row = QHBoxLayout()
        self.dot0 = QLabel("●")
        self.dot1 = QLabel("○")
        for dot in [self.dot0, self.dot1]:
            dot.setAlignment(Qt.AlignCenter)
            dot.setFont(QFont("Arial", 14))
            dot.setStyleSheet("color:#333333;")
            indicator_row.addWidget(dot)
        root.addLayout(indicator_row)

        self.stack = QStackedWidget()
        self.sonar_page = SonarPage()
        self.env_page   = EnvPage()
        self.stack.addWidget(self.sonar_page)
        self.stack.addWidget(self.env_page)
        root.addWidget(self.stack)

        hint = QLabel("◀                 ▶")
        hint.setAlignment(Qt.AlignCenter)
        hint.setFont(QFont("Arial", 9))
        hint.setStyleSheet("color:#aaaaaa;")
        root.addWidget(hint)

        signals.sonar_updated.connect(self.sonar_page.update_sonar)
        signals.env_updated.connect(self.env_page.update_env)
        signals.btn_received.connect(self.on_btn)

    def on_btn(self, btn: str):
        current = self.stack.currentIndex()
        if btn == "7":
            idx = max(0, current - 1)
        elif btn == "8":
            idx = min(self.stack.count() - 1, current + 1)
        else:
            return
        self.stack.setCurrentIndex(idx)
        self.dot0.setText("●" if idx == 0 else "○")
        self.dot1.setText("●" if idx == 1 else "○")
        print(f"[PAGE] {'초음파' if idx == 0 else '환경센서'} 페이지")

if __name__ == "__main__":
    threading.Thread(target=udp_listen, daemon=True).start()

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())