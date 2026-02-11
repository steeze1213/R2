class Map:

    dict_enum = {
        "0": " ■ ",     #Wall
        "1": "   ",     #Road
        "2": " ? ",
        "3": " ? ",
        "4": " ? ",
        "5": " ဝိူ ",     #Player
        "6": " ☆ ",     #Exit
        "7": " 𖢥 ",     #Monster
        "8": " ? ",
        "9": " ? ",
        "10": " P ",
        "11": " ? ",
        "15": " ✞ ",    #Heal
        "16": " 🗲 ",    #Attack
        "17": "  ꙰ "    #Defense
    }


    def __init__(self, file_path: str):
        self.file_path = file_path
        self.array = []        # 인스턴스 변수
        self.monster_num = 0   # 인스턴스 변수

        with open(file_path, "r") as f:
            for line in f:
                line = line.replace(" ", "").replace("\n", "")
                self.array.append(line.split(","))


    def get_map_array(self) -> list:
        return self.array

    def change_map(self, orign_x : int , orign_y : int,
                   change_num : int ,
                   new_x : int, new_y : int, new_num :int ):
        self.array[orign_x][orign_y] = str(change_num)
        self.array[new_x][new_y] = str(new_num)


    def get_monster_num(self) -> int:
        return self.monster_num

    def draw_map(self, manual_lines=None):
        self.monster_num = 0

        for i in range(20):
            row = ""
            for j in range(20):
                if self.array[i][j] == "7":
                    self.monster_num += 1
                row += self.dict_enum[self.array[i][j]]

            # 오른쪽 메뉴얼 붙이기
            if manual_lines and i < len(manual_lines):
                print(row + "   " + manual_lines[i])
            else:
                print(row)

if __name__ != '__main__':
    print("잘못된 호출입니다.")