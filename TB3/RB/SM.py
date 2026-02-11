import math
import time
from flask import Flask, request, jsonify
import threading

# 시뮬레이션 설정
PORT = 9010

MAP_W = 3.0   # m
MAP_H = 5.0   # m

LIDAR_RANGE = 3.5
LIDAR_RES = 360
DT = 0.05

# 장애물 정의
# (x1, y1, x2, y2)
OBSTACLES = [
    # 외곽 벽
    (0.0, 0.0, MAP_W, 0.0),
    (MAP_W, 0.0, MAP_W, MAP_H),
    (MAP_W, MAP_H, 0.0, MAP_H),
    (0.0, MAP_H, 0.0, 0.0),

    # 내부 장애물
    # 상단 가로 벽
    (0.3, 4.8, 2.7, 4.8),

    # 중앙에서 내려오는 세로 벽 (T자)
    (1.5, 4.8, 1.5, 3.0),

    # 작은 정사각형 장애물
    # 크기: 0.025m × 0.025m
    # 위치: 로봇 전방 0.5m (중심: 1.5, 1.1)

    # 아래 변
    (1.4875, 1.0875, 1.5125, 1.0875),
    # 오른쪽 변
    (1.5125, 1.0875, 1.5125, 1.1125),
    # 위 변
    (1.5125, 1.1125, 1.4875, 1.1125),
    # 왼쪽 변
    (1.4875, 1.1125, 1.4875, 1.0875),
]

# 로봇 상태
robot = {
    "x": MAP_W / 2.0,
    "y": 0.6,
    "a": math.pi / 2,
    "lin": 0.0,
    "ang": 0.0,
}

lock = threading.Lock()
app = Flask(__name__)

# 기하 유틸
def ray_segment_intersect(rx, ry, rdx, rdy, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    det = (-rdx * vy + rdy * vx)
    if abs(det) < 1e-6:
        return None

    s = (-vy * (x1 - rx) + vx * (y1 - ry)) / det
    t = ( rdx * (y1 - ry) - rdy * (x1 - rx)) / det

    if s >= 0 and 0 <= t <= 1:
        return s
    return None

def cast_ray(x, y, ang):
    dx = math.cos(ang)
    dy = math.sin(ang)
    min_d = LIDAR_RANGE

    for (x1, y1, x2, y2) in OBSTACLES:
        d = ray_segment_intersect(x, y, dx, dy, x1, y1, x2, y2)
        if d is not None and d < min_d:
            min_d = d

    return min_d

# LiDAR 생성
def generate_lidar():
    scan = []
    for i in range(LIDAR_RES):
        ang = robot["a"] + math.radians(i)
        d = cast_ray(robot["x"], robot["y"], ang)
        scan.append(int(d * 100))  # cm
    return scan

# 물리 업데이트
def sim_loop():
    while True:
        with lock:
            robot["a"] += robot["ang"] * DT
            robot["x"] += math.cos(robot["a"]) * robot["lin"] * DT
            robot["y"] += math.sin(robot["a"]) * robot["lin"] * DT

            # 맵 바깥 방지
            robot["x"] = max(0.05, min(MAP_W - 0.05, robot["x"]))
            robot["y"] = max(0.05, min(MAP_H - 0.05, robot["y"]))

        time.sleep(DT)

# API
@app.route("/control", methods=["GET"])
def control():
    with lock:
        if "lin" in request.args:
            robot["lin"] = float(request.args["lin"])
        if "ang" in request.args:
            robot["ang"] = float(request.args["ang"])

        return jsonify({
            "p": {
                "x": robot["x"],
                "y": robot["y"],
                "a": robot["a"]
            },
            "s": generate_lidar()
        })

# 실행
if __name__ == "__main__":
    threading.Thread(target=sim_loop, daemon=True).start()
    print("Sim server running on port 9010")
    app.run(host="0.0.0.0", port=PORT, debug=False)