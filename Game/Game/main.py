import msvcrt #window 콘솔 입력 처리,키입력:kbhit(), 키읽기:getch()
import os #cls(화면 지우기), pause
import random #몬스터 이동 방향 무작위 선택, 몬스터 공격확률50%
#내부 모듈
from game_package import map_module #맵 파일(txt)->2차원 배열 관리+출력
from game_package import player #플레이어 좌표, 체력, 이동, 공격, 버프 로직
from game_package import monster #몬스터 좌표, 이동, 체력, 공격 판정
from game_package import item #아이템 코드 정의 및 효과 처리

#스테이지 파일 절대경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))#stage1~3까지 실행위치 상관없이 불러오기

# 오른쪽에 표시될 게임 메뉴얼
MANUAL_LINES = [
    "🎮 GAME MANUAL 🎮",
    "",
    "이동 : W A S D",
    "",
    "공격 : R (주변 8칸)",
    "",
    "",
    "꙰ 아이템 🗲",
    "",
    "✞ : HP +1 (최대 3)",
    "",
    "🗲 : 다음 공격력 2 (1회)",
    "",
    " ꙰ : 몬스터 공격 1회 무효",
]



def draw(): #콘솔 화면 전체 초기화, 이전 출력 잔상 제거
    os.system("cls")

    # HP 표시
    hp = player_.get_hp()
    max_hp = player_.max_hp #항상 피 최대 3
    hearts = "♥ " * hp + "♡ " * (max_hp - hp)
    print(f"HP: {hearts}")

    # 버프 표시 (A / B)
    buffs = []
    if hasattr(player_, "buff_attack") and player_.buff_attack:
        buffs.append("🗲") #공격력 증가 버프 A(1회)
    if hasattr(player_, "buff_block") and player_.buff_block:
        buffs.append("꙰") #방어력 증가 버프 B(1회)

    print("BUFF:", " ".join(buffs) if buffs else "-") #버프가 없을 경우 "-" 출력
    print()
    # 스테이지 정보, 현재 스테이지 번호 / 전체 스테이지 수
    print(f"STAGE : {current_stage_index + 1} / {len(stage_files)}")
    print()

    map_.draw_map(MANUAL_LINES) #맵 출력, 내부 20x20 2차원 배열 순회하며 콘솔 출력 + 오른쪽 메뉴얼 표시


def load_stage(stage_path): #스테이지 전환 시 호출
    global map_, monsters_, player_ # 맵, 몬스터 플레이어 상태 새로 구성

    # 스테이지 시작시 플레이어 상태 초기화
    player_.reset_status()

    # 맵 로드
    map_ = map_module.Map(stage_path)

    # 몬스터 초기화
    monsters_ = []

    # 플레이어 / 몬스터 위치 세팅
    for i in range(20):
        for j in range(20):
            if map_.get_map_array()[i][j] == "5": #플레이어 시작 위치 설정
                player_.set_position(j, i) #좌표 규칙 (x=j, y=i)

            elif map_.get_map_array()[i][j] == "7": #몬스터 생성 위치
                m = monster.Monster(3) #체력 3 공격 1
                m.set_position(j, i)
                monsters_.append(m)

    draw() #스테이지 로드 직후 화면 출력

# ---------------- Stage 관리 ----------------
stage_files = [
    os.path.join(BASE_DIR, "stage1.txt"),
    os.path.join(BASE_DIR, "stage2.txt"),
    os.path.join(BASE_DIR, "stage3.txt"),
]

current_stage_index = 0 #현재 진행 중인 스테이지 인덱스

#Awake--------------------------------------------------------------------------//
#Class 인스턴스 초기화

map_ = map_module.Map(stage_files[current_stage_index]) #첫 스테이지 맵

player_ = player.Player(3,3,1,False) #플레이어 HP 최대 3 현재 3

monsters_ = [] #load_stage에서 채워짐



#Start--------------------------------------------------------------------------//

load_stage(stage_files[current_stage_index])

draw()


#Update--------------------------------------------------------------------------//

while 1: #메인 루프, 게임 종료까지 반복, 1회 루프 == 1틱

    if msvcrt.kbhit(): #키 입력이 있을 때만
        key = msvcrt.getch()

        # ---------------------------attack----------------------------------------
        if key in (b'r', b'R'):
            attack_positions = player_.get_attack_targets(map_.get_map_array()) #플레이어 주변 8칸 좌표 목록 반환

            for m in monsters_[:]:#리스트 복사본, 순회 중 제거해도 에러 방지용

                if m.get_position() in attack_positions: #공격 범위 내 몬스터 데미지 적용
                    m.take_damage(player_.attack_power)
                    player_.consume_attack_buff() #공격 버프 있으면 즉시 소모
                    if m.is_dead(): #몬스터 사망 시 리스트에서 제거 + 맵 타일로 변경
                        mx, my = m.get_position()
                        map_.change_map(my, mx, 1, my, mx, 1)
                        monsters_.remove(m)


            draw()
            continue # 공격을하면 몬스터가 움직이게하지않기 위해
        # -----------------------------player------------------------------------------

        origin_x, origin_y = player_.get_position() #이동 전 좌표 저장
        movecode = player_.movement(key, map_.get_map_array())

        if movecode != "f": #이동한 위치 타일 코드 확인
            nx, ny = player_.get_position()
            target = map_.get_map_array()[ny][nx]

            # H 아이템 (15): 체력 +1 (최대면 효과 없음), 아이템은 사라짐

            # ---------------- Item 처리 ----------------

            if item.handle_item(
                    target,
                    player_,
                    map_,
                    origin_y, origin_x,
                    ny, nx
            ):
                draw()
                continue

            # 도착지
            if target == "6":

                # 마지막 스테이지면 게임 클리어
                if current_stage_index == len(stage_files) - 1:
                    print("\n 모든 스테이지를 클리어했습니다!")
                    print("게임 클리어!")
                    os.system("pause")
                    exit(0)

                # 다음 스테이지로 이동
                current_stage_index += 1
                print(f"\n ▶ 다음 스테이지로 이동합니다 ({current_stage_index + 1})")
                os.system("pause")
                load_stage(stage_files[current_stage_index])
                continue

            map_.change_map(origin_y, origin_x, 1, ny, nx, 5)
        #-----------------------------monster------------------------------------------

        for m in monsters_: #각 몬스터 랜덤 이동 시도
            m_origin_position = m.get_position()  # monster origin position
            m_movecode = m.monster_movement(map_.get_map_array())  # monster new position

            if m_movecode != "f":
                 map_.change_map(m_origin_position[1], m_origin_position[0], 1,
                        m.get_position()[1], m.get_position()[0], 7)

        # ---------------------- monster attack ----------------------
        px, py = player_.get_position() #플레이어 좌표

        for m in monsters_: #몬스터 좌표

            # 플레이어 주변 8칸 이내
            if m.monster_attack(px,py):
                if player_.consume_block_buff():
                        continue  #방어 버프로 이번 공격 무효

                player_.t_damage() #플레이어 체력 감소

                draw()

                if player_.dead(): #체력 0 게임 종료
                    draw()
                    print("\nGAME OVER")
                    os.system("pause")
                    exit(0)
        # -------------------------------------------------------------

        draw()