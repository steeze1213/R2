import math
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from collections import deque
from datetime import datetime
import requests
import threading
import time
import mysql.connector
import os

SOURCE_NAME = os.path.splitext(os.path.basename(__file__))[0]

db_conn = mysql.connector.connect(
    host="192.168.0.187",
    port=3306,
    user="root",
    password="0000",
    database="group1",
    autocommit=True
)
db_cursor = db_conn.cursor()

# ================= 설정 및 파라미터 =================
URL = "http://127.0.0.1:9010/control"
#URL = "http://192.168.0.243:9271/control"
INTERVAL = 80  # UI 갱신 주기 (메인 스레드, 렉 방지)
FETCH_INTERVAL = 0.05  # API 폴링 주기 (백그라운드)
PATH_HISTORY_MAX = 600

CANVAS_SIZE = 600
SCALE = 1.5  # cm → px

# 도달 판정 범위 (cm)
WP_TOL = 1.0  # 도착 판정 반경 (웨이포인트/탐색)
PARK_TOL = 1.0  # 주차(복귀) 위치 오차 허용 반경 (10cm)
WP_ARRIVAL_CONSEC = 2  # 연속 N회 내에 있어야 도착 인정
ANGLE_TOL = math.radians(0.5)  # 주차 시 회전 완료 판정각 (±2도)
ANGLE_ARRIVAL_CONSEC = 2  # 주차 각도 연속 도착 인정 횟수

# 주차 정렬(회전) 비례 제어 파라미터
PARK_ALIGN_P_GAIN = 0.8  # 비례 제어 gain (오차에 비례한 속도)
PARK_ALIGN_MAX_SPEED = 0.2  # 최대 회전 속도 (큰 오차시)
PARK_ALIGN_MIN_SPEED = 0.1  # 최소 회전 속도 (정지 직전)

# smart_move 제어 파라미터
SLOW_DIST_CM = 15.0  # 이 거리 이하에서 1차 감속
NEAR_DIST_CM = 8.0  # 이 거리 이하에서 2차 강감속
MIN_LIN_SPEED = 0.05  # 중간 구간 최소 속도
MIN_LIN_SPEED_NEAR = 0.02  # 근접 구간 최소 속도 (오버슈트 방지)
ROT_THRESHOLD = 0.52  # 이 각도 이상이면 제자리 회전만 함 (약 30도) - 먼저 회전 후 직진
ANG_GAIN = 1.8  # 각도 보정 gain
ALIGN_SLOW_THRESHOLD = 0.2  # 복귀 정렬 시 저속 회전 전환각 (rad)
ALIGN_SLOW_FACTOR = 0.3  # 저속 회전 배율 (더 정확한 정렬)

# 탐색(Search) 설정
SEARCH_RADIUS = 40.0
SEARCH_SQUARE_RADIUS = 25.0  # 사각형 패턴 반경
SEARCH_POINTS = 60
SEARCH_CIRCLE_POINTS = 30

# LIDAR 시각화 설정
DIST_DIV = 100.0
MIN_DIST = 0.10
MAX_DIST = 3.5
LIDAR_SKIP = 2  # LIDAR 표시 간격 (전체 표시)
PATH_DISPLAY_STEP = 2  # 경로 흔적 표시 시 2칸마다 1점 (600→300점)
LIDAR_SCALE_CM = 100  # LIDAR m → cm (DIST_DIV 적용 후)

GRID_CM = 20
GRID_COLOR = "#dddddd"
WALL_COLOR = "#7a00cc"
PATH_COLOR = "#ffcc00"
WAYPOINT_COLOR = "#007bff"
SEARCH_COLOR = "#9c27b0"
VISUAL_OFFSET = math.pi / 2

# 폰트 설정
FONT_MAIN = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")

# 유효한 탐색 패턴
VALID_PATTERNS = frozenset({"나선형", "원형", "사각형", "하트"})

# 장애물 판정 (cm 이하면 장애물로 인식)
OBSTACLE_THRESHOLD_CM = 30.0
FRONT_OBSTACLE_DISTANCE = 30.0  # 전방 장애물 감지 거리 (cm)
FRONT_OBSTACLE_COUNT = 5  # 장애물로 판정할 최소 LIDAR 포인트 수

# 회피 동작 파라미터
AVOIDANCE_MIN_FORWARD_CM = 30.0  # 회피 후 최소 전진 거리 (cm)

# 벽/장애물 분류 파라미터
CLUSTER_DIST_JUMP_CM = 20.0  # 클러스터 분리 거리 차이 기준
WALL_MIN_LENGTH_CM = 80.0  # 벽으로 보는 최소 길이
WALL_MAX_MEAN_RESID_CM = 5.0  # 직선 적합 평균 잔차
WALL_MIN_POINTS = 6  # 벽 판단 최소 포인트 수


class RobotController(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        # [개발자 설정] 내부 속도 변수
        self.cfg_lin_speed = 0.25
        self.cfg_ang_speed = 0.6

        self.rx = self.ry = self.ra = 0.0
        self.start_pose = None
        self.mode = "IDLE"
        self.return_phase = None

        # 장애물 회피 관련 변수
        self.in_avoidance = False  # 회피 중 여부
        self.avoidance_forward_distance = 0.0  # 회피 중 전진한 거리
        self.avoidance_target_waypoint = None  # 회피 전 목표 waypoint
        self.last_waypoint_distance = 0.0  # 회피 시작 시 waypoint까지의 거리
        self.avoidance_has_rotated = False  # 회피 시작 시 회전 완료 여부

        self.lidar_data = []
        self.waypoints = []
        self.search_waypoints = []
        self.path_history = deque(maxlen=PATH_HISTORY_MAX)  # O(1) append, 자동 크기 제한

        self.search_pattern = tk.StringVar(value="--선택--")
        self.auto_search = tk.BooleanVar(value=False)

        self.log_entries = deque(maxlen=100)
        self._last_log_time = 0
        self._log_interval_sec = 0.5
        self._arrival_count = 0  # 도착 연속 카운트 (스쳐지나감 방지)
        self._last_mode = "IDLE"  # 상태 변화 감지용

        # 탐색 시각화
        self.search_window = None
        self._search_path_started = False

        self.setup_ui()
        threading.Thread(target=self.fetch_loop, daemon=True).start()
        threading.Thread(target=self.control_loop, daemon=True).start()
        self.update_loop()

    # ================= UI 구성 =================
    def setup_ui(self):
        panel = tk.Frame(self, width=260, padx=10, pady=10)
        panel.pack(side="left", fill="y")

        tk.Label(panel, text="[ 위치 정보 ]", font=FONT_BOLD).pack(anchor="w")
        self.lbl_start_pos = tk.Label(panel, text="Start: X: 0.00, Y: 0.00, A: 0.0°", fg="#666666", font=FONT_MAIN)
        self.lbl_start_pos.pack(anchor="w", pady=(5, 0))
        self.lbl_current_pos = tk.Label(panel, text="Current: X: 0.00, Y: 0.00, A: 0.0°",
                                        font=FONT_BOLD, fg="#007bff")
        self.lbl_current_pos.pack(anchor="w", pady=(0, 5))
        self.lbl_state = tk.Label(panel, text="상태: IDLE", font=FONT_MAIN)
        self.lbl_state.pack(anchor="w", pady=5)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=8)

        # 1. 일반 주행 제어
        tk.Label(panel, text="[ 기본 주행 ]", font=FONT_BOLD).pack(anchor="w")
        tk.Button(panel, text="포인트 따라가기", command=self.start_waypoints, font=FONT_MAIN).pack(fill="x", pady=2)
        tk.Button(panel, text="최단 경로 설정", command=self.optimize_path, font=FONT_MAIN).pack(fill="x", pady=2)
        tk.Button(panel, text="경로 초기화", command=self.clear_waypoints, font=FONT_MAIN).pack(fill="x", pady=2)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=8)

        # 2. 탐색(Search) 제어
        tk.Label(panel, text="[ 탐색 모드 ]", font=FONT_BOLD).pack(anchor="w")
        pat_combo = ttk.Combobox(panel, textvariable=self.search_pattern,
                                 values=["나선형", "원형", "사각형", "하트"], state="readonly", font=FONT_MAIN)
        pat_combo.pack(fill="x", pady=2)
        tk.Checkbutton(panel, text="주행 후 자동 탐색", variable=self.auto_search, font=FONT_MAIN).pack(anchor="w")
        tk.Button(panel, text="탐색 시작", command=self.start_search, font=FONT_MAIN).pack(fill="x", pady=4)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=8)

        # 3. 복귀 및 정지
        tk.Label(panel, text="[ 복귀 설정 ]", font=FONT_BOLD).pack(anchor="w")
        pf = tk.Frame(panel)
        pf.pack(anchor="w")
        self.park_var = tk.StringVar(value="BACK")
        tk.Radiobutton(pf, text="전면주차", variable=self.park_var, value="FRONT", font=FONT_MAIN).pack(side="left")
        tk.Radiobutton(pf, text="후면주차", variable=self.park_var, value="BACK", font=FONT_MAIN).pack(side="left")
        tk.Button(panel, text="복귀하기", command=self.start_return, font=FONT_MAIN).pack(fill="x", pady=5)

        tk.Button(panel, text="정지", command=self.stop_robot,
                  fg="white", bg="#d32f2f", font=FONT_BOLD).pack(fill="x", pady=15)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=8)
        self.btn_log_toggle = tk.Button(panel, text="📋 로그 열기", command=self.toggle_log,
                                        font=("Segoe UI", 11, "bold"),
                                        fg="white", bg="#2196F3",
                                        padx=12, pady=10, cursor="hand2", relief=tk.RAISED, bd=2)
        self.btn_log_toggle.pack(fill="x", pady=8)

        # 중앙: 캔버스 + (접을 수 있는) 로그 패널
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(side="right", expand=True, fill="both")

        self.canvas = tk.Canvas(self.content_frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="white")
        self.canvas.pack(side="left", expand=True, fill="both")
        self.canvas.bind("<Button-1>", self.add_waypoint_click)

        # 로그 패널 (우측, 기본 숨김)
        self.log_frame = tk.Frame(self.content_frame, width=360, bg="white", relief=tk.GROOVE, bd=1)
        self.log_frame.pack_propagate(False)
        self._log_visible = False

        log_header = tk.Frame(self.log_frame, bg="white", pady=6)
        log_header.pack(fill="x", padx=8)
        tk.Label(log_header, text="[ 로봇 상태 로그 ]", font=FONT_BOLD, fg="#333", bg="white").pack(side="left")
        tk.Button(log_header, text="접기", command=self.toggle_log, font=FONT_MAIN,
                  fg="#666", relief=tk.FLAT, cursor="hand2").pack(side="right")

        self.log_text = scrolledtext.ScrolledText(
            self.log_frame, wrap=tk.WORD, font=("Consolas", 9),
            bg="white", fg="#333", insertbackground="#333",
            relief=tk.FLAT, padx=8, pady=4
        )
        self.log_text.pack(expand=True, fill="both")

    def toggle_log(self):
        """로그 패널 열기/접기"""
        if self._log_visible:
            self.log_frame.pack_forget()
            self.btn_log_toggle.config(text="📋 로그 열기", bg="#2196F3")
            self._log_visible = False
        else:
            self.log_frame.pack(side="right", fill="y")
            self.btn_log_toggle.config(text="📋 로그 접기", bg="#1976D2")
            self._log_visible = True

    def get_obstacle_info(self):
        """LIDAR에서 장애물 방향·거리 분석. 반환: (감지여부, [(방향, 거리_cm), ...])"""
        if not self.lidar_data or len(self.lidar_data) < 360:
            return False, []

        def get_dist_cm(deg):
            idx = deg % 360
            raw = self.lidar_data[idx]
            if raw <= 0:
                return float("inf")
            d_m = raw / DIST_DIV
            return d_m * 100  # m → cm

        # 전방(-20~20), 좌(70~90), 우(270~290), 후방(160~200)
        front = min(get_dist_cm(d) for d in range(-20, 21))
        left = min(get_dist_cm(d) for d in range(70, 91))
        right = min(get_dist_cm(d) for d in range(270, 291))
        back = min(get_dist_cm(d) for d in range(160, 201))

        obstacles = []
        if front < OBSTACLE_THRESHOLD_CM:
            obstacles.append(("전방", front))
        if left < OBSTACLE_THRESHOLD_CM:
            obstacles.append(("좌측", left))
        if right < OBSTACLE_THRESHOLD_CM:
            obstacles.append(("우측", right))
        if back < OBSTACLE_THRESHOLD_CM:
            obstacles.append(("후방", back))

        return len(obstacles) > 0, obstacles

    def check_front_obstacle(self):
        """전방 장애물 감지: 전방 각도 범위에서 기준 거리 이내 포인트 수"""
        dists = self.get_lidar_dist_cm_list()
        if not dists:
            return False

        # 전방 범위: 0~44도, 315~359도
        front_angles = list(range(0, 45)) + list(range(315, 360))
        obstacle_count = 0

        for angle in front_angles:
            if dists[angle] <= FRONT_OBSTACLE_DISTANCE:
                obstacle_count += 1

        return obstacle_count >= FRONT_OBSTACLE_COUNT

    def get_front_obstacle_distance(self):
        """전방 장애물 최소 거리(cm). 감지 없으면 inf 반환"""
        dists = self.get_lidar_dist_cm_list()
        if not dists:
            return float("inf")

        front_angles = list(range(0, 45)) + list(range(315, 360))
        front_dists = [dists[a] for a in front_angles if math.isfinite(dists[a])]
        if not front_dists:
            return float("inf")
        return min(front_dists)

    def detect_front_obstacle_type(self):
        """
        전방 30cm 범위의 장애물 타입 감지
        반환: ("wall" | "obstacle" | None, 감지된 개수)
        """
        dists = self.get_lidar_dist_cm_list()
        if not dists:
            return None, 0

        types = self.classify_lidar_points(dists)

        # 전방 범위: 0~44도, 315~359도
        front_angles = list(range(0, 45)) + list(range(315, 360))

        wall_count = 0
        obstacle_count = 0

        for angle in front_angles:
            if dists[angle] <= FRONT_OBSTACLE_DISTANCE:
                if types[angle] == "wall":
                    wall_count += 1
                elif types[angle] == "obstacle":
                    obstacle_count += 1

        # 어느 것이 더 많은지 판단
        if wall_count + obstacle_count < FRONT_OBSTACLE_COUNT:
            return None, 0

        if wall_count > obstacle_count:
            return "wall", wall_count
        else:
            return "obstacle", obstacle_count

    def get_best_turn_direction(self):
        """
        현재 방향 기준 좌우 중 더 비어있는 방향 판단
        - 더 먼 평균 거리
        - 장애물로 잡히는 포인트가 적은 쪽
        반환: ("left" | "right", 좌측거리, 우측거리, 좌측카운트, 우측카운트)
        """
        dists = self.get_lidar_dist_cm_list()
        if not dists:
            return None, 0, 0, 0, 0

        # 현재 방향 기준 좌우 스캔 범위 (더 넓은 범위)
        # 좌측: 20~160도, 우측: 200~340도
        left_angles = list(range(20, 161))
        right_angles = list(range(200, 341))

        left_dists = [dists[a] for a in left_angles if math.isfinite(dists[a])]
        right_dists = [dists[a] for a in right_angles if math.isfinite(dists[a])]

        left_avg = sum(left_dists) / len(left_dists) if left_dists else 0
        right_avg = sum(right_dists) / len(right_dists) if right_dists else 0

        left_count = sum(1 for a in left_angles if dists[a] <= FRONT_OBSTACLE_DISTANCE)
        right_count = sum(1 for a in right_angles if dists[a] <= FRONT_OBSTACLE_DISTANCE)

        # 점수: 평균거리 우선 + 장애물 포인트 수가 적은 쪽 우선
        # (동점이면 평균거리가 큰 쪽)
        if left_count < right_count:
            return "left", left_avg, right_avg, left_count, right_count
        if right_count < left_count:
            return "right", left_avg, right_avg, left_count, right_count

        if left_avg >= right_avg:
            return "left", left_avg, right_avg, left_count, right_count
        return "right", left_avg, right_avg, left_count, right_count

    def rotate_90_degrees(self, direction):
        """
        90도 회전 (방향: "left" 또는 "right")
        direction: "left" → 반시계방향 90도 회전
                   "right" → 시계방향 90도 회전
        """
        target_angle = self.ra + (math.pi / 2 if direction == "left" else -math.pi / 2)

        print(
            f"[회전 시작] 방향: {direction} (90도) | 현재: {math.degrees(self.ra):.1f}° → 목표: {math.degrees(target_angle):.1f}°")

        # 90도 회전 완료될 때까지 회전
        rotate_start_time = time.time()
        while time.time() - rotate_start_time < 5.0:  # 최대 5초
            err = (target_angle - self.ra + math.pi) % (2 * math.pi) - math.pi

            if abs(err) < math.radians(2):  # ±2도 이내
                self.send_cmd(0, 0)
                print(f"[회전 완료] {math.degrees(self.ra):.1f}°")
                break

            # 회전 명령
            ang_cmd = 0.5 if err > 0 else -0.5  # 회전 속도 0.5 rad/s
            self.send_cmd(0, ang_cmd)
            time.sleep(0.05)

    def rotate_to_angle(self, target_angle):
        """목표 절대 각도(target_angle)로 회전"""
        target_angle = target_angle % (2 * math.pi)
        rotate_start_time = time.time()
        while time.time() - rotate_start_time < 5.0:  # 최대 5초
            err = (target_angle - self.ra + math.pi) % (2 * math.pi) - math.pi
            if abs(err) < math.radians(2):
                self.send_cmd(0, 0)
                break
            ang_cmd = 0.5 if err > 0 else -0.5
            self.send_cmd(0, ang_cmd)
            time.sleep(0.05)

    def get_front_wall_parallel_angle(self):
        """전방 벽과 평행한 방향(절대 각도) 계산. 실패 시 None"""
        dists = self.get_lidar_dist_cm_list()
        if not dists:
            return None

        types = self.classify_lidar_points(dists)
        front_angles = list(range(0, 45)) + list(range(315, 360))

        wall_points = []
        for angle_deg in front_angles:
            if types[angle_deg] == "wall" and dists[angle_deg] < 100:
                r = dists[angle_deg]
                theta = math.radians(angle_deg)
                x = r * math.cos(theta)
                y = r * math.sin(theta)
                wall_points.append((x, y))

        if len(wall_points) < 3:
            return None

        xs = [p[0] for p in wall_points]
        ys = [p[1] for p in wall_points]
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        numerator = sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs)))
        denominator = sum((xs[i] - mx) ** 2 for i in range(len(xs)))

        if abs(denominator) < 1e-6:
            wall_angle = math.pi / 2
        else:
            slope = numerator / denominator
            wall_angle = math.atan(slope)

        return (self.ra + wall_angle) % (2 * math.pi)

    def can_reach_waypoint_directly(self, target_x, target_y):
        """
        현재 위치에서 목표 waypoint까지 직진할 수 있는지 확인
        (목표 방향 범위 내에 장애물이 없는지 체크)
        반환: True = 장애물 없음, False = 장애물 있음
        """
        dists = self.get_lidar_dist_cm_list()
        if not dists:
            return True

        # 목표 방향 계산
        target_angle = math.atan2(target_y - self.ry, target_x - self.rx)
        relative_angle = (target_angle - self.ra + math.pi) % (2 * math.pi) - math.pi
        target_deg = int(math.degrees(relative_angle)) % 360

        # 목표 방향 ±30도 범위 내 장애물 확인
        check_angles = [(target_deg + offset) % 360 for offset in range(-30, 31)]

        obstacle_count = 0
        for angle in check_angles:
            if dists[angle] <= FRONT_OBSTACLE_DISTANCE:
                obstacle_count += 1

        # 충분한 포인트 수 이상 장애물이 있으면 막혀있음
        return obstacle_count < FRONT_OBSTACLE_COUNT

    def get_lidar_dist_cm_list(self):
        if not self.lidar_data or len(self.lidar_data) < 360:
            return None
        dists = []
        for i in range(360):
            raw = self.lidar_data[i]
            if raw <= 0:
                dists.append(float("inf"))
            else:
                dists.append((raw / DIST_DIV) * 100)
        return dists

    def classify_lidar_points(self, dists):
        """클러스터링 후 벽/장애물 분류. 반환: 각도 인덱스별 타입"""
        types = [None] * 360

        # 클러스터 분리
        clusters = []
        current = []
        prev_dist = None
        for deg in range(360):
            dist = dists[deg]
            if not math.isfinite(dist):
                if current:
                    clusters.append(current)
                    current = []
                prev_dist = None
                continue

            if not current:
                current = [deg]
            else:
                if prev_dist is not None and abs(dist - prev_dist) > CLUSTER_DIST_JUMP_CM:
                    clusters.append(current)
                    current = [deg]
                else:
                    current.append(deg)
            prev_dist = dist

        if current:
            clusters.append(current)

        # 클러스터 분류
        for cluster in clusters:
            if len(cluster) < WALL_MIN_POINTS:
                ctype = "obstacle"
            else:
                pts = []
                for deg in cluster:
                    r = dists[deg]
                    th = math.radians(deg)
                    pts.append((r * math.cos(th), r * math.sin(th)))

                # 길이 추정
                x0, y0 = pts[0]
                x1, y1 = pts[-1]
                length = math.hypot(x1 - x0, y1 - y0)

                # PCA로 직선성 평가
                mx = sum(p[0] for p in pts) / len(pts)
                my = sum(p[1] for p in pts) / len(pts)
                sxx = sum((p[0] - mx) ** 2 for p in pts) / len(pts)
                syy = sum((p[1] - my) ** 2 for p in pts) / len(pts)
                sxy = sum((p[0] - mx) * (p[1] - my) for p in pts) / len(pts)

                trace = sxx + syy
                det = sxx * syy - sxy * sxy
                temp = max(0.0, (trace / 2) ** 2 - det)
                lambda2 = trace / 2 - math.sqrt(temp)
                mean_resid = math.sqrt(max(0.0, lambda2))

                if length >= WALL_MIN_LENGTH_CM and mean_resid <= WALL_MAX_MEAN_RESID_CM:
                    ctype = "wall"
                else:
                    ctype = "obstacle"

            for deg in cluster:
                types[deg] = ctype

        # None은 장애물로 취급
        for i in range(360):
            if types[i] is None:
                types[i] = "obstacle"

        return types

    def format_log_line(self):
        """현재 상태를 로그 한 줄로 포맷"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pos = f"X: {self.rx / 100:.2f}m, Y: {self.ry / 100:.2f}m"
        state = self.mode
        if self.mode == "RETURN" and self.return_phase:
            state = f"{self.mode}({self.return_phase})"

        detected, obstacles = self.get_obstacle_info()
        if detected:
            obs_str = " | ".join(f"{d}: {r:.0f}cm" for d, r in obstacles)
            obs_info = f"감지됨 [{obs_str}]"
        else:
            obs_info = "없음"

        # 전방 감지 대상(벽/장애물) 로그 표시
        front_type = "없음"
        dists = self.get_lidar_dist_cm_list()
        if dists:
            types = self.classify_lidar_points(dists)
            front_angles = list(range(0, 45)) + list(range(315, 360))
            wall_count = 0
            obs_count = 0
            for a in front_angles:
                if dists[a] <= FRONT_OBSTACLE_DISTANCE:
                    if types[a] == "wall":
                        wall_count += 1
                    else:
                        obs_count += 1
            if wall_count or obs_count:
                if wall_count > obs_count:
                    front_type = "벽"
                elif obs_count > wall_count:
                    front_type = "장애물"
                else:
                    front_type = "혼합"

        return f"[{now}] Pos({pos}) | 상태: {state} | 장애물: {obs_info} | 전방: {front_type}\n"

    def update_log(self):
        """로그 창에 새 줄 추가"""
        try:
            line = self.format_log_line()
            self.log_text.insert(tk.END, line)
            self.log_text.see(tk.END)
            # 스크롤 영역 제한 (최근 500줄)
            lines = self.log_text.get("1.0", tk.END).split("\n")
            if len(lines) > 500:
                self.log_text.delete("1.0", f"{len(lines) - 500}.0")

            # DB 저장
            state = self.mode
            if self.mode == "RETURN" and self.return_phase:
                state = f"{self.mode}({self.return_phase})"

            pos_x = self.rx / 100.0
            pos_y = self.ry / 100.0

            detected, obstacles = self.get_obstacle_info()
            obstacle_flag = bool(detected)
            obstacle_desc = None
            if detected and obstacles:
                obstacle_desc = ", ".join(
                    f"{direction}:{int(dist)}cm" for direction, dist in obstacles
                )

            front_type = "없음"
            dists = self.get_lidar_dist_cm_list()
            if dists:
                types = self.classify_lidar_points(dists)
                front_angles = list(range(0, 45)) + list(range(315, 360))
                wall_cnt = 0
                obs_cnt = 0
                for a in front_angles:
                    if dists[a] <= FRONT_OBSTACLE_DISTANCE:
                        if types[a] == "wall":
                            wall_cnt += 1
                        else:
                            obs_cnt += 1
                if wall_cnt > obs_cnt:
                    front_type = "벽"
                elif obs_cnt > wall_cnt:
                    front_type = "장애물"
                elif wall_cnt or obs_cnt:
                    front_type = "혼합"

            db_cursor.execute(
                """
                INSERT INTO log (
                    source, level, message,
                    rx, ry, theta,
                    state, pos_x, pos_y,
                    obstacle, obstacle_desc, front_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    SOURCE_NAME,
                    "INFO",
                    line.strip(),
                    self.rx,
                    self.ry,
                    self.ra,
                    state,
                    pos_x,
                    pos_y,
                    obstacle_flag,
                    obstacle_desc,
                    front_type,
                )
            )
        except (tk.TclError, AttributeError):
            pass
        except Exception:
            pass

    def fetch_loop(self):
        """API 요청 전용 스레드 - 메인(GUI) 스레드 블로킹 방지"""
        while True:
            try:
                res = requests.get(URL, timeout=0.1).json()
                p = res["p"]
                self.rx, self.ry, self.ra = p["x"] * 100, p["y"] * 100, float(p["a"])
                # 각도 정규화 (0 ~ 2π 범위)
                self.ra = self.ra % (2 * math.pi)
                if self.start_pose is None:
                    self.start_pose = (self.rx, self.ry, self.ra)
                self.path_history.append((self.rx, self.ry))
                self.lidar_data = res.get("s", res.get("scan", []))
            except (requests.RequestException, KeyError, ValueError, TypeError):
                pass
            time.sleep(FETCH_INTERVAL)

    # ================= 핵심 제어 로직 =================
    def control_loop(self):
        while True:
            # 회피 모드 중인지 확인
            if self.in_avoidance:
                # 장애물 회피 중: 먼저 벽과 평행하게 회전 후 직진
                if not self.avoidance_has_rotated:
                    target_angle = self.get_front_wall_parallel_angle()
                    if target_angle is not None:
                        self.send_cmd(0, 0)
                        self.rotate_to_angle(target_angle)
                    else:
                        direction, left_dist, right_dist, left_count, right_count = self.get_best_turn_direction()
                        self.send_cmd(0, 0)
                        self.rotate_90_degrees(direction)
                    self.avoidance_has_rotated = True

                # 회전 후 고정 거리만 전진
                # 전진 중 다시 장애물이 나타나면 센서 갱신 후 재회전
                if self.check_front_obstacle():
                    obstacle_type, count = self.detect_front_obstacle_type()
                    if obstacle_type:
                        print(f"[회피 중 재감지] {obstacle_type.upper()} ({count}포인트) → 재회전")
                        direction, left_dist, right_dist, left_count, right_count = self.get_best_turn_direction()
                        print(
                            f"  좌측: {left_dist:.1f}cm({left_count}), 우측: {right_dist:.1f}cm({right_count}) → {direction} 방향")
                        self.send_cmd(0, 0)
                        self.rotate_90_degrees(direction)
                        self.avoidance_has_rotated = True
                else:
                    self.send_cmd(self.cfg_lin_speed, 0)
                    # cfg_lin_speed는 m/s, 거리 누적은 cm 단위
                    self.avoidance_forward_distance += self.cfg_lin_speed * 0.05 * 100

                if self.avoidance_forward_distance >= AVOIDANCE_MIN_FORWARD_CM:
                    # 전진 완료 후 waypoint로 복귀
                    self.in_avoidance = False
                    self.avoidance_forward_distance = 0.0
                    self.avoidance_has_rotated = False
            else:
                # 회피 모드 아님: 일반 제어
                if self.check_front_obstacle():
                    # 장애물/벽 감지 → 회피 모드 진입
                    obstacle_type, count = self.detect_front_obstacle_type()

                    if obstacle_type:
                        print(f"[장애물 감지] {obstacle_type.upper()} ({count}포인트) → 회피 시작")
                        self.send_cmd(0, 0)

                        # 장애물보다 앞에 있는 waypoint만 도착 처리
                        if self.mode == "WAYPOINT" and self.waypoints:
                            front_dist = self.get_front_obstacle_distance()
                            wp_dist = math.hypot(
                                self.waypoints[0][0] - self.rx,
                                self.waypoints[0][1] - self.ry
                            )

                            if wp_dist <= front_dist:
                                reached = self.waypoints.pop(0)
                                print(f"[웨이포인트 도착 처리] 장애물보다 앞이라 {reached} 도착으로 처리")
                            else:
                                print("[웨이포인트 유지] 장애물 뒤에 있어 삭제하지 않음")

                            # 다음 waypoint를 회피 종료 조건으로 사용
                            if self.waypoints:
                                self.avoidance_target_waypoint = self.waypoints[0]
                                self.last_waypoint_distance = math.hypot(
                                    self.waypoints[0][0] - self.rx,
                                    self.waypoints[0][1] - self.ry
                                )
                            else:
                                self.avoidance_target_waypoint = None

                        # 더 비어있는 방향 판단 및 회전
                        direction, left_dist, right_dist, left_count, right_count = self.get_best_turn_direction()
                        print(
                            f"  좌측: {left_dist:.1f}cm({left_count}), 우측: {right_dist:.1f}cm({right_count}) → {direction} 방향 회전")
                        # 회피 모드 진입 (회전은 회피 모드에서 수행)
                        self.in_avoidance = True
                        self.avoidance_forward_distance = 0.0
                        self.avoidance_has_rotated = False
                    else:
                        # 타입 미결정: 일단 멈춤
                        self.send_cmd(0, 0)
                else:
                    # 장애물 없음: 모드별 제어 실행
                    if self.mode == "WAYPOINT":
                        self.step_waypoint()
                    elif self.mode == "SEARCH":
                        self.step_search()
                    elif self.mode == "RETURN":
                        self.step_return()

            time.sleep(0.05)

    def smart_move(self, tx, ty, dist_tol=WP_TOL, allow_in_place=True):
        dist = math.hypot(tx - self.rx, ty - self.ry)

        # 도착 판정:
        # - 회피 모드: 30cm 범위 적용 (장애물 회피 후)
        # - 일반 모드: dist_tol(5cm) 정확한 범위 적용
        arrival_tol = FRONT_OBSTACLE_DISTANCE if self.in_avoidance else dist_tol

        if dist < arrival_tol:
            self._arrival_count += 1
            if self._arrival_count >= WP_ARRIVAL_CONSEC:
                self._arrival_count = 0
                return True
        else:
            self._arrival_count = 0

        ta = math.atan2(ty - self.ry, tx - self.rx)
        err = (ta - self.ra + math.pi) % (2 * math.pi) - math.pi

        limit_lin, limit_ang = self.cfg_lin_speed, self.cfg_ang_speed
        # 2단계 감속: 15cm→8cm→근접 순으로 점진적 감속
        if dist > SLOW_DIST_CM:
            target_lin = limit_lin
        elif dist > NEAR_DIST_CM:
            target_lin = max(MIN_LIN_SPEED, limit_lin * (dist / SLOW_DIST_CM))
        else:
            target_lin = max(MIN_LIN_SPEED_NEAR, limit_lin * (dist / NEAR_DIST_CM) * 0.5)

        if allow_in_place:
            # ===== 개선된 제어 로직: 먼저 회전 정렬, 그다음 직진 =====
            if abs(err) > 0.1:  # 각도 오차가 있으면 제자리 회전만
                rot_speed = limit_ang if abs(err) > 0.8 else limit_ang * 0.6
                self.send_cmd(0, rot_speed if err > 0 else -rot_speed)
            else:  # 각도 정렬됨: 직진
                self.send_cmd(target_lin, 0)
        else:
            # 웨이포인트는 좌표 도달 위주: 제자리 회전 없이 이동 중 보정
            ang_cmd = max(-limit_ang, min(limit_ang, err * ANG_GAIN))
            lin_cmd = target_lin * (0.5 if abs(err) > ROT_THRESHOLD else 1.0)
            self.send_cmd(lin_cmd, ang_cmd)
        return False

    def step_waypoint(self):
        if not self.waypoints:
            if self.auto_search.get() and self.start_search():
                pass  # start_search가 SEARCH 모드로 전환
            else:
                self.stop_robot()
            return
        if self.smart_move(*self.waypoints[0], allow_in_place=True):
            self.waypoints.pop(0)
            self.send_cmd(0, 0)
            time.sleep(0.1)

    def step_search(self):
        if not self.search_waypoints:
            self.stop_robot()
            return
        if self.smart_move(*self.search_waypoints[0]):
            self.search_waypoints.pop(0)

    def step_return(self):
        if not self.start_pose:
            print("DEBUG: start_pose가 None")
            return
        sx, sy, sa = self.start_pose
        print(f"DEBUG: return_phase = {self.return_phase}")
        if self.return_phase == "MOVE":
            dist = math.hypot(sx - self.rx, sy - self.ry)
            print(
                f"DEBUG: MOVE 단계 - 목표({sx / 100:.2f}, {sy / 100:.2f}) 현재({self.rx / 100:.2f}, {self.ry / 100:.2f}) 거리={dist:.2f}cm 허용={PARK_TOL:.4f}")
            if self.smart_move(sx, sy, dist_tol=PARK_TOL):
                print("DEBUG: MOVE 단계 도착! ALIGN으로 전환")
                self.send_cmd(0, 0)
                self.return_phase = "ALIGN"
                self._align_arrival_count = 0
        elif self.return_phase == "ALIGN":
            # 목표 각도: 시작할 때의 각도
            target_yaw = sa
            # 각도 오차 계산 (최단 거리로 자동 계산)
            err_yaw = (target_yaw - self.ra + math.pi) % (2 * math.pi) - math.pi

            # 디버그 출력
            print(
                f"목표: {math.degrees(target_yaw):.1f}° | 현재: {math.degrees(self.ra):.1f}° | 오차: {math.degrees(err_yaw):.1f}° | 범위: {math.degrees(ANGLE_TOL):.1f}°")

            if abs(err_yaw) < ANGLE_TOL:
                # 오차 범위 내: 연속 카운트로 안정성 확보
                self._align_arrival_count += 1
                self.send_cmd(0, 0)
                if self._align_arrival_count >= ANGLE_ARRIVAL_CONSEC:
                    self.stop_robot()
            else:
                self._align_arrival_count = 0
                # 비례 제어: 오차에 비례한 회전 속도
                rot_speed = abs(err_yaw) * PARK_ALIGN_P_GAIN

                # 목표 각도에 가까워지면 느리게 회전
                if abs(err_yaw) < ALIGN_SLOW_THRESHOLD:
                    rot_speed *= ALIGN_SLOW_FACTOR

                # 회전 속도 제한
                rot_speed = max(PARK_ALIGN_MIN_SPEED, min(PARK_ALIGN_MAX_SPEED, rot_speed))

                # err_yaw > 0: 목표가 더 큼 (반시계 회전 필요)
                # err_yaw < 0: 목표가 더 작음 (시계 회전 필요)
                # 더 가까운 방향으로 자동 선택됨
                print(f"회전 속도: {rot_speed:.3f} | 방향: {'반시계(+)' if err_yaw > 0 else '시계(-)'}")
                self.send_cmd(0, rot_speed if err_yaw > 0 else -rot_speed)

    # ================= 탐색 패턴 & 유틸 =================
    def start_search(self):
        pattern = self.search_pattern.get()
        if pattern not in VALID_PATTERNS:
            messagebox.showwarning("탐색 모드", "나선형, 원형, 사각형, 하트 중 패턴을 선택해 주세요.")
            return False

        cx, cy = (self.waypoints[-1] if self.waypoints else (self.rx, self.ry))
        pts = []

        if pattern == "나선형":
            for i in range(SEARCH_POINTS):
                t = i / SEARCH_POINTS
                pts.append((
                    cx + SEARCH_RADIUS * t * math.cos(t * 8 * math.pi),
                    cy + SEARCH_RADIUS * t * math.sin(t * 8 * math.pi),
                ))
        elif pattern == "원형":
            for i in range(SEARCH_CIRCLE_POINTS):
                th = 2 * math.pi * i / SEARCH_CIRCLE_POINTS
                pts.append((cx + SEARCH_RADIUS * math.cos(th), cy + SEARCH_RADIUS * math.sin(th)))
        elif pattern == "사각형":
            r = SEARCH_SQUARE_RADIUS
            for y in (-r, 0, r):
                pts.append((cx - r, cy + y))
                pts.append((cx + r, cy + y))
        elif pattern == "하트":
            for i in range(SEARCH_POINTS):
                t = 2 * math.pi * i / SEARCH_POINTS
                x = 16 * math.sin(t) ** 3
                y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
                pts.append((cx + x * 2, cy + y * 2))

        self.search_waypoints = pts
        if self.search_window is None:
            self.search_window = SearchMapWindow(self, self.search_waypoints)
        else:
            self.search_window.reset_path(self.search_waypoints)

        self.mode = "SEARCH"
        self._arrival_count = 0
        self._search_path_started = True
        return True

    def add_waypoint_click(self, event):
        if len(self.waypoints) >= 5:
            messagebox.showwarning("입력 제한", "웨이포인트는 최대 5개까지만 설정할 수 있습니다.")
            return
        cx, cy = CANVAS_SIZE // 2, CANVAS_SIZE // 2
        dx, dy = (event.x - cx) / SCALE, (cy - event.y) / SCALE
        d = math.hypot(dx, dy)
        a = math.atan2(dy, dx) + self.ra - VISUAL_OFFSET
        self.waypoints.append((self.rx + d * math.cos(a), self.ry + d * math.sin(a)))

    def update_loop(self):
        """UI 전용 루프 (네트워크 없음, 메인 스레드 논블로킹)"""
        if self.start_pose is not None:
            self.lbl_start_pos.config(
                text=(
                    f"Start: X: {self.start_pose[0] / 100:.2f}, Y: {self.start_pose[1] / 100:.2f}, "
                    f"A: {math.degrees(self.start_pose[2]):.1f}°"
                )
            )
        self.lbl_current_pos.config(
            text=(
                f"Current: X: {self.rx / 100:.2f}, Y: {self.ry / 100:.2f}, "
                f"A: {math.degrees(self.ra):.1f}°"
            )
        )
        self.lbl_state.config(text=f"상태: {self.mode}")
        self.draw_canvas()

        # 로그: 로봇이 작동 중일 때만 주기적으로 찍음, IDLE 전환 시 1회만 찍음
        is_active = self.mode != "IDLE"
        mode_changed = self.mode != self._last_mode

        if mode_changed:
            self._last_log_time = time.time()
            self.update_log()  # 상태 변화 시 즉시 1회 로그
        elif is_active and time.time() - self._last_log_time >= self._log_interval_sec:
            self._last_log_time = time.time()
            self.update_log()  # 활동 중일 때만 주기적 로그

        self._last_mode = self.mode

        self.after(INTERVAL, self.update_loop)

        # 탐색 시각화
        if self.search_window:
            try:
                self.search_window.draw_lidar_obstacle(
                    self.rx, self.ry, self.ra, self.lidar_data
                )
                if self.mode == "SEARCH":
                    self.search_window.update_robot(
                        self.rx, self.ry, self.ra
                    )
            except tk.TclError:
                self.search_window = None

    def draw_canvas(self):
        self.canvas.delete("all")
        cx, cy = CANVAS_SIZE // 2, CANVAS_SIZE // 2

        def to_canvas(wx, wy):
            dx, dy = wx - self.rx, wy - self.ry
            d = math.hypot(dx, dy)
            a = math.atan2(dy, dx) - self.ra + VISUAL_OFFSET
            return cx + d * math.cos(a) * SCALE, cy - d * math.sin(a) * SCALE

        # 그리드
        grid_step = int(GRID_CM * SCALE)
        for i in range(0, CANVAS_SIZE, grid_step):
            self.canvas.create_line(i, 0, i, CANVAS_SIZE, fill=GRID_COLOR)
            self.canvas.create_line(0, i, CANVAS_SIZE, i, fill=GRID_COLOR)

        # LIDAR (cos/sin 한 번만 계산)
        for i in range(0, len(self.lidar_data), LIDAR_SKIP):
            d = self.lidar_data[i] / DIST_DIV
            if MIN_DIST < d < MAX_DIST:
                ang = math.radians(i) + VISUAL_OFFSET
                px = cx + d * LIDAR_SCALE_CM * math.cos(ang) * SCALE
                py = cy - d * LIDAR_SCALE_CM * math.sin(ang) * SCALE
                self.canvas.create_rectangle(px, py, px + 2, py + 2, fill=WALL_COLOR, outline="")

        # 경로 흔적 (포인트 많을 때 샘플링으로 렌더링 부하 감소)
        if len(self.path_history) > 1:
            hist = list(self.path_history)
            if len(hist) > 150:
                hist = hist[::PATH_DISPLAY_STEP]
            flat_pts = [c for pt in hist for c in to_canvas(pt[0], pt[1])]
            if len(flat_pts) >= 4:
                self.canvas.create_line(flat_pts, fill=PATH_COLOR, width=2)

        # 웨이포인트
        prev = (cx, cy)
        for wx, wy in self.waypoints:
            sx, sy = to_canvas(wx, wy)
            self.canvas.create_line(prev[0], prev[1], sx, sy, fill=WAYPOINT_COLOR, dash=(4, 2))
            self.canvas.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill=WAYPOINT_COLOR, outline="white")
            prev = (sx, sy)

        # 탐색 경로
        if self.search_waypoints:
            s_pts = [c for pt in self.search_waypoints for c in to_canvas(pt[0], pt[1])]
            if len(s_pts) >= 4:
                self.canvas.create_line(s_pts, fill=SEARCH_COLOR, width=1, dash=(2, 2))

        # 로봇
        self.canvas.create_oval(cx - 12, cy - 12, cx + 12, cy + 12, fill="blue", width=2)
        self.canvas.create_line(cx, cy, cx, cy - 25, fill="red", arrow=tk.LAST, width=3)

    def start_waypoints(self):
        self.mode = "WAYPOINT" if self.waypoints else "IDLE"
        self._arrival_count = 0

    def start_return(self):
        self.return_phase = "MOVE"
        self.mode = "RETURN"
        self._arrival_count = 0

    def stop_robot(self):
        self.mode = "IDLE";
        self.send_cmd(0, 0)

    def clear_waypoints(self):
        self.waypoints.clear()
        self.search_waypoints.clear()
        self.path_history.clear()

    def optimize_path(self):
        """동적 프로그래밍으로 최적 경로 계산 (TSP 문제 해결)"""
        if len(self.waypoints) < 2:
            return

        points = [(self.rx, self.ry)] + self.waypoints
        n = len(points)

        if n <= 2:
            return

        # 거리 함수
        def dist(i, j):
            return math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1])

        # 모든 점 간 거리 행렬
        dist_matrix = [[dist(i, j) for j in range(n)] for i in range(n)]

        # DP[mask][i] = 방문한 점들(비트마스크), 현재 위치 i일 때의 최단거리
        INF = float('inf')
        dp = [[INF] * n for _ in range(1 << n)]
        parent = [[-1] * n for _ in range(1 << n)]

        # 시작점(0)에서 시작
        dp[1][0] = 0

        # 모든 부분집합 상태 순회
        for mask in range(1 << n):
            for u in range(n):
                if dp[mask][u] == INF or not ((mask >> u) & 1):
                    continue
                # u에서 방문하지 않은 다음 점으로
                for v in range(n):
                    if (mask >> v) & 1:  # 이미 방문
                        continue
                    new_mask = mask | (1 << v)
                    new_dist = dp[mask][u] + dist_matrix[u][v]
                    if new_dist < dp[new_mask][v]:
                        dp[new_mask][v] = new_dist
                        parent[new_mask][v] = u

        # 모든 점 방문한 최종 상태에서 가장 가까운 점
        full_mask = (1 << n) - 1
        last = min(range(1, n), key=lambda i: dp[full_mask][i])

        # 경로 역추적
        path = []
        mask = full_mask
        curr = last
        while curr != 0:
            path.append(curr)
            prev = parent[mask][curr]
            mask ^= (1 << curr)
            curr = prev

        path.reverse()

        # 웨이포인트만 추출
        self.waypoints = [points[i] for i in path]

    def send_cmd(self, lin, ang):
        try:
            requests.get(URL, params={"lin": f"{lin:.3f}", "ang": f"{ang:.3f}"}, timeout=0.1)
        except requests.RequestException:
            pass


# ___________________________________________________탐색 시각화___________________________________________________
class SearchMapWindow:
    """
    탐색 전용 확대 지도 창
    - world-fixed view
    - 탐색 경로 전체 표시
    - 장애물(LIDAR) 누적 표시
    """

    def __init__(self, parent, search_waypoints):
        self.win = tk.Toplevel(parent)
        self.win.title("Search Map View")
        self.win.geometry("700x700")

        self.canvas_size = 650
        self.canvas = tk.Canvas(
            self.win, width=self.canvas_size, height=self.canvas_size, bg="white"
        )
        self.canvas.pack(expand=True, fill="both")

        self.search_waypoints = list(search_waypoints)
        self._recalc_scale()
        self.draw_search_path()

        self.robot_path = []
        self.search_started = False

    def _recalc_scale(self):
        xs = [p[0] for p in self.search_waypoints] if self.search_waypoints else [0]
        ys = [p[1] for p in self.search_waypoints] if self.search_waypoints else [0]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)

        span = max(self.max_x - self.min_x, self.max_y - self.min_y)
        self.scale = (self.canvas_size * 0.8) / max(span, 1)
        self.origin_x = self.canvas_size / 2
        self.origin_y = self.canvas_size / 2

    def reset_path(self, search_waypoints):
        self.canvas.delete("all")
        self.search_waypoints = list(search_waypoints)
        self._recalc_scale()
        self.draw_search_path()
        self.robot_path = []
        self.search_started = False

    def world_to_canvas(self, x, y):
        cx = self.origin_x + (x - (self.min_x + self.max_x) / 2) * self.scale
        cy = self.origin_y - (y - (self.min_y + self.max_y) / 2) * self.scale
        return cx, cy

    def draw_search_path(self):
        pts = []
        for x, y in self.search_waypoints:
            pts.extend(self.world_to_canvas(x, y))
        if len(pts) >= 4:
            self.canvas.create_line(
                pts, fill=SEARCH_COLOR, width=2, dash=(3, 2)
            )

    def draw_lidar_obstacle(self, rx, ry, ra, lidar_data):
        for i in range(0, len(lidar_data), LIDAR_SKIP):
            d = lidar_data[i] / DIST_DIV
            if MIN_DIST < d < MAX_DIST:
                ang = math.radians(i)
                wx = rx + d * 100 * math.cos(ang + ra)
                wy = ry + d * 100 * math.sin(ang + ra)
                cx, cy = self.world_to_canvas(wx, wy)
                self.canvas.create_rectangle(
                    cx, cy, cx + 2, cy + 2,
                    fill=WALL_COLOR, outline=""
                )

    def update_robot(self, rx, ry, ra):
        if not self.search_started:
            self.search_started = True
        self.robot_path.append((rx, ry))
        self.draw_robot_path()
        self.draw_robot(rx, ry, ra)

    def draw_robot_path(self):
        if len(self.robot_path) < 2:
            return
        pts = []
        for x, y in self.robot_path:
            pts.extend(self.world_to_canvas(x, y))
        if len(pts) >= 4:
            self.canvas.create_line(
                pts,
                fill=PATH_COLOR,
                width=2
            )

    def draw_robot(self, rx, ry, ra):
        self.canvas.delete("robot")
        cx, cy = self.world_to_canvas(rx, ry)
        self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="blue", width=1, tags="robot")
        hx = cx + 12 * math.cos(ra)
        hy = cy - 12 * math.sin(ra)
        self.canvas.create_line(cx, cy, hx, hy, fill="red", arrow=tk.LAST, width=2, tags="robot")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("1조")
    RobotController(root).pack(expand=True, fill="both")
    root.mainloop()