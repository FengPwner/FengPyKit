import random
import time

class Game:
    def __init__(self):
        self.player = {"name": "", "hp": 100, "max_hp": 100, "atk": 15, "gold": 0, "level": 1, "exp": 0, "potions": 3}
        self.monsters = [
            {"name": "史莱姆", "hp": 30, "atk": 8, "exp": 20, "gold": 10},
            {"name": "哥布林", "hp": 50, "atk": 12, "exp": 35, "gold": 20},
            {"name": "骷髅兵", "hp": 70, "atk": 16, "exp": 50, "gold": 30},
            {"name": "兽人", "hp": 100, "atk": 20, "exp": 70, "gold": 50},
            {"name": "恶龙", "hp": 150, "atk": 25, "exp": 100, "gold": 100},
        ]
        self.shop_items = [
            {"name": "生命药水", "price": 30, "effect": "heal"},
            {"name": "铁剑", "price": 80, "effect": "atk_up"},
            {"name": "钢剑", "price": 150, "effect": "atk_up2"},
        ]

    def print_slow(self, text, delay=0.02):
        for char in text:
            print(char, end="", flush=True)
            time.sleep(delay)
        print()

    def show_status(self):
        print(f"\n{'='*40}")
        print(f"  {self.player['name']} | Lv.{self.player['level']} | HP: {self.player['hp']}/{self.player['max_hp']}")
        print(f"  攻击: {self.player['atk']} | 金币: {self.player['gold']} | 药水: {self.player['potions']}")
        print(f"{'='*40}\n")

    def choose_name(self):
        name = input("请输入你的角色名: ").strip()
        self.player["name"] = name if name else "勇者"
        print(f"\n欢迎你，{self.player['name']}！冒险即将开始...\n")

    def explore(self):
        self.print_slow("你踏入了未知的荒野...")
        time.sleep(0.5)
        event = random.choice(["battle", "battle", "battle", "treasure", "nothing"])
        if event == "battle":
            self.battle()
        elif event == "treasure":
            gold = random.randint(10, 50)
            self.player["gold"] += gold
            self.print_slow(f"你发现了一个宝箱，获得 {gold} 金币！")
        else:
            self.print_slow("四周静悄悄的，什么也没发生。")

    def battle(self):
        monster = random.choice(self.monsters[:min(len(self.monsters), self.player["level"] + 1)])
        m = {"name": monster["name"], "hp": monster["hp"], "atk": monster["atk"], "exp": monster["exp"], "gold": monster["gold"]}
        self.print_slow(f"\n遭遇了 {m['name']} (HP:{m['hp']}, ATK:{m['atk']})！")
        while m["hp"] > 0 and self.player["hp"] > 0:
            print("\n1.攻击  2.使用药水  3.逃跑")
            choice = input("选择行动: ").strip()
            if choice == "1":
                dmg = random.randint(self.player["atk"] - 3, self.player["atk"] + 3)
                m["hp"] -= dmg
                self.print_slow(f"你对 {m['name']} 造成 {dmg} 点伤害！(剩余HP:{max(0,m['hp'])})")
                if m["hp"] <= 0:
                    break
            elif choice == "2":
                if self.player["potions"] > 0:
                    self.player["potions"] -= 1
                    heal = 40
                    self.player["hp"] = min(self.player["max_hp"], self.player["hp"] + heal)
                    self.print_slow(f"你使用了药水，恢复 {heal} 点HP。")
                else:
                    self.print_slow("没有药水了！")
                    continue
            elif choice == "3":
                if random.random() > 0.5:
                    self.print_slow("你成功逃跑了！")
                    return
                else:
                    self.print_slow("逃跑失败！")
            else:
                continue
            mdmg = random.randint(m["atk"] - 2, m["atk"] + 2)
            self.player["hp"] -= mdmg
            self.print_slow(f"{m['name']} 攻击了你，造成 {mdmg} 点伤害！(你的HP:{max(0,self.player['hp'])})")
        if self.player["hp"] <= 0:
            self.print_slow("\n你被击败了...游戏结束。")
            self.show_status()
            return False
        self.print_slow(f"\n你击败了 {m['name']}！获得 {m['exp']} 经验和 {m['gold']} 金币。")
        self.player["exp"] += m["exp"]
        self.player["gold"] += m["gold"]
        self.level_up()
        return True

    def level_up(self):
        need = self.player["level"] * 100
        while self.player["exp"] >= need:
            self.player["exp"] -= need
            self.player["level"] += 1
            self.player["max_hp"] += 20
            self.player["hp"] = self.player["max_hp"]
            self.player["atk"] += 5
            self.print_slow(f"\n升级了！当前等级: {self.player['level']}，HP和攻击力提升！")
            need = self.player["level"] * 100

    def shop(self):
        print("\n=== 商店 ===")
        for i, item in enumerate(self.shop_items):
            print(f"{i+1}. {item['name']} - {item['price']}金币")
        print("0.离开")
        choice = input("选择购买: ").strip()
        if choice == "0":
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.shop_items):
                item = self.shop_items[idx]
                if self.player["gold"] >= item["price"]:
                    self.player["gold"] -= item["price"]
                    if item["effect"] == "heal":
                        self.player["potions"] += 1
                        print("购买了生命药水！")
                    elif item["effect"] == "atk_up":
                        self.player["atk"] += 5
                        print("购买了铁剑！攻击力+5")
                    elif item["effect"] == "atk_up2":
                        self.player["atk"] += 10
                        print("购买了钢剑！攻击力+10")
                else:
                    print("金币不足！")
        except ValueError:
            print("无效选择。")

    def rest(self):
        self.print_slow("你在营地休息，恢复了部分体力...")
        self.player["hp"] = min(self.player["max_hp"], self.player["hp"] + 30)
        print(f"当前HP: {self.player['hp']}/{self.player['max_hp']}")

    def run(self):
        self.choose_name()
        alive = True
        while alive:
            self.show_status()
            print("1.探索  2.商店  3.休息  4.退出")
            choice = input("选择行动: ").strip()
            if choice == "1":
                alive = self.explore()
            elif choice == "2":
                self.shop()
            elif choice == "3":
                self.rest()
            elif choice == "4":
                print("感谢游玩！再见。")
                break
            else:
                print("无效选择。")

if __name__ == "__main__":
    Game().run()