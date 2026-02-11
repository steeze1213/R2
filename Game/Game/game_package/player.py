# 플레이어 모듈
#
# 플레이어의 위치(x, y) 관리
# 이동 가능 여부 판단 (맵 충돌 체크)
# 체력(HP) 관리 및 사망 판정
# 공격 범위 계산 (주변 8칸)
# 아이템 효과 상태 관리 (공격 / 방어 버프)
#
# 실제 전투 판정(몬스터 제거, 데미지 적용)은
# main.py 또는 monster 모듈에서 처리함
#
# [좌표 규칙 정리]
# map_module의 grid는 2차원 리스트
# 접근 방식: grid[y][x]
#
# y : 행(row)
# x : 열(col)
#
# 이동 시 좌표 변화
# w (위)    : y - 1
# s (아래)  : y + 1
# a (왼쪽)  : x - 1
# d (오른쪽): x + 1
#
# ※ 이 규칙을 Player / Monster / Map 모두 동일하게 사용


class Player :

    x = 0
    y = 0

    def __init__(self, max_hp_ : int, hp_ : int, attack_count_ : int, defense_ : bool):

        # item, main이 직접 참조하는 필드들
        self.max_hp = max_hp_ # 최대 체력 3
        self.hp = hp_ # 현재 체력 3

        self.attack_power = 1 #기본 공격력
        self.buff_attack = False #A 아이템 활성 여부
        self.buff_block = False #B 아이템 활성 여부

    def set_position(self, x, y): #맵 로딩 시 시작 위치 지정
        self.x = x
        self.y = y

    def get_position(self): #main, monster 공격 판정에서 사용
        return self.x, self.y

    def get_hp(self): #현재 체력 반환
        return int(self.hp)

    def set_hp(self, hp): #체력 값 보정
        # hp는 0~max_hp로 제한
        hp = int(hp)
        if hp < 0:
            hp = 0
        if hp > int(self.max_hp):
            hp = int(self.max_hp)
        self.hp = hp

    def movement(self, key: bytes, grid: list) -> str:
        walk_able = ("1", "6", "15", "16", "17")
        # 1길, 6출구, 15회복, 16공격, 17방어
        # wasd 이동
        if key == b'w':
            if self.y - 1 >= 0 and grid[self.y - 1][self.x] in walk_able:
                self.y -= 1
                return "w"

        elif key == b'a':
            if self.x - 1 >= 0 and grid[self.y][self.x - 1] in walk_able:
                self.x -= 1
                return "a"

        elif key == b's':
            if self.y + 1 < 20 and grid[self.y + 1][self.x] in walk_able:
                self.y += 1
                return "s"

        elif key == b'd':
            if self.x + 1 < 20 and grid[self.y][self.x + 1] in walk_able:
                self.x += 1
                return "d"



        #이동 실패(벽, 몬스터)
        return "f"

    def t_damage(self):
        # 피격: hp 1 감소(최소 0)
        self.set_hp(self.get_hp() - 1)
        return self.get_hp()

    def dead(self):
        # 사망: hp <= 0
        return self.get_hp() <= 0

    def get_attack_targets(self, grid):
        # 주변 8칸 좌표를 리스트로 반환 (유효 범위만)
        targets = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue  # 자기 자신 제외
                nx, ny = self.x + dx, self.y + dy
                if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]):
                    targets.append((nx, ny))
        return targets

    def heal(self): # 회복 +1
        if self.hp < self.max_hp: #체력이 이미 최대면 X
            self.hp += 1
            return True
        return False

    def consume_attack_buff(self): # 공격 아이템
        if self.buff_attack:
            self.buff_attack = False
            self.attack_power = 1

    def consume_block_buff(self): # 방어 아이템
        if self.buff_block:
            self.buff_block = False
            return True
        return False

    def reset_status(self): #스테이지 이동 시 호출
        self.hp = self.max_hp
        self.attack_power = 1
        self.buff_attack = False
        self.buff_block = False


if __name__ != '__main__':
    print("잘못된 호출입니다.")