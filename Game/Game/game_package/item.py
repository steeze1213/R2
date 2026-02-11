class ItemBase:

    code: str  # 예: "15", "16", "17"

    x: int
    y: int

    def apply(self, player):
        raise NotImplementedError("Item must implement apply()")

class HealItem(ItemBase):
    code = "15"

    def apply(self, player):
        # 체력 +1 (최대 체력 초과 불가)
        player.heal()

class AttackItem(ItemBase):
    code = "16"

    def apply(self, player):
        # 다음 공격력 2 (1회)
        player.attack_power = 2
        player.buff_attack = True

class DefenseItem(ItemBase):
    code = "17"

    def apply(self, player):
        # 몬스터 공격 1회 무효
        player.buff_block = True

ITEM_REGISTRY = {
    HealItem.code: HealItem(),
    AttackItem.code: AttackItem(),
    DefenseItem.code: DefenseItem(),
}
def handle_item(target_tile: str, player, map_, oy, ox, ny, nx) -> bool:

    item = ITEM_REGISTRY.get(target_tile)
    if not item:
        return False  # 아이템 타일이 아님

    # 아이템 효과 적용
    item.apply(player)

    # 아이템을 먹은 뒤 플레이어 이동 + 아이템 제거
    map_.change_map(oy, ox, 1, ny, nx, 5)
    return True