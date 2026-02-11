import random

class Monster:
    def __init__(self, hp: int):
        self.x = 0
        self.y = 0
        self.hp = hp

    def set_position(self, x, y):
        self.x, self.y = x, y

    def get_position(self):
        return self.x, self.y

    def take_damage(self, amount: int):
        self.hp -= amount

    def is_dead(self):
        return self.hp <= 0

    def monster_movement(self, grid: list) -> str:
        direction = random.randint(0, 3)

        if direction == 0 and self.y - 1 >= 0 and grid[self.y - 1][self.x] == "1":
            self.y -= 1
            return "w"

        if direction == 1 and self.y + 1 < len(grid) and grid[self.y + 1][self.x] == "1":
            self.y += 1
            return "s"

        if direction == 2 and self.x - 1 >= 0 and grid[self.y][self.x - 1] == "1":
            self.x -= 1
            return "a"

        if direction == 3 and self.x + 1 < len(grid[0]) and grid[self.y][self.x + 1] == "1":
            self.x += 1
            return "d"

        return "f"

    def monster_attack(self, player_x : int, player_y: int) -> bool:

        if abs(self.x - player_x) <= 1 and abs(self.y - player_y) <= 1:
            #50% 확률 공격
            if random.random() < 0.5:
                return True

        return False