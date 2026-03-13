"""
DnD 5e 战斗追踪器
管理先攻顺序、回合、HP、状态效果
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from scripts.dice import roll


@dataclass
class Combatant:
    """战斗参与者"""
    name: str
    initiative: int = 0
    max_hp: int = 10
    current_hp: int = 10
    ac: int = 10
    is_player: bool = True
    player_id: str = ""
    conditions: List[str] = field(default_factory=list)
    # NPC/怪物专用
    attack_bonus: int = 0
    damage_dice: str = "1d6"
    damage_bonus: int = 0

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    @property
    def is_bloodied(self) -> bool:
        """半血以下"""
        return 0 < self.current_hp <= self.max_hp // 2


@dataclass
class CombatTracker:
    """战斗管理器"""
    combatants: List[Combatant] = field(default_factory=list)
    round_number: int = 0
    current_turn: int = 0
    is_active: bool = False
    log: List[str] = field(default_factory=list)

    def add_combatant(self, combatant: Combatant):
        """添加战斗参与者"""
        self.combatants.append(combatant)

    def add_monster(self, name: str, hp: int, ac: int, attack_bonus: int = 0,
                    damage_dice: str = "1d6", damage_bonus: int = 0,
                    initiative_mod: int = 0):
        """快速添加怪物"""
        init_roll = roll(f"1d20+{initiative_mod}" if initiative_mod >= 0 else f"1d20{initiative_mod}")
        monster = Combatant(
            name=name,
            initiative=init_roll.total,
            max_hp=hp,
            current_hp=hp,
            ac=ac,
            is_player=False,
            attack_bonus=attack_bonus,
            damage_dice=damage_dice,
            damage_bonus=damage_bonus
        )
        self.combatants.append(monster)
        return init_roll

    def sort_initiative(self):
        """按先攻排序（高到低）"""
        self.combatants.sort(key=lambda c: c.initiative, reverse=True)

    def start_combat(self):
        """开始战斗"""
        self.sort_initiative()
        self.round_number = 1
        self.current_turn = 0
        self.is_active = True
        self.log = []

    def get_current_combatant(self) -> Optional[Combatant]:
        """获取当前行动者"""
        if not self.is_active or not self.combatants:
            return None
        alive = [c for c in self.combatants if c.is_alive]
        if not alive:
            return None
        return self.combatants[self.current_turn % len(self.combatants)]

    def next_turn(self) -> Optional[Combatant]:
        """推进到下一个回合"""
        if not self.is_active:
            return None

        # 跳过已死亡的
        attempts = 0
        while attempts < len(self.combatants):
            self.current_turn += 1
            if self.current_turn >= len(self.combatants):
                self.current_turn = 0
                self.round_number += 1
            current = self.combatants[self.current_turn]
            if current.is_alive:
                return current
            attempts += 1

        # 所有人都死了
        self.end_combat()
        return None

    def deal_damage(self, target_name: str, damage: int) -> str:
        """对目标造成伤害"""
        for c in self.combatants:
            if c.name.lower() == target_name.lower():
                c.current_hp = max(0, c.current_hp - damage)
                status = ""
                if not c.is_alive:
                    status = f" 💀 {c.name} 倒下了！"
                elif c.is_bloodied:
                    status = f" 🩸 {c.name} 受了重伤！"
                return f"{c.name} 受到 {damage} 点伤害 (HP: {c.current_hp}/{c.max_hp}){status}"
        return f"找不到目标: {target_name}"

    def heal(self, target_name: str, amount: int) -> str:
        """治疗目标"""
        for c in self.combatants:
            if c.name.lower() == target_name.lower():
                c.current_hp = min(c.max_hp, c.current_hp + amount)
                return f"{c.name} 恢复 {amount} 点生命 (HP: {c.current_hp}/{c.max_hp})"
        return f"找不到目标: {target_name}"

    def add_condition(self, target_name: str, condition: str) -> str:
        """添加状态效果"""
        for c in self.combatants:
            if c.name.lower() == target_name.lower():
                if condition not in c.conditions:
                    c.conditions.append(condition)
                return f"{c.name} 获得状态: {condition}"
        return f"找不到目标: {target_name}"

    def remove_condition(self, target_name: str, condition: str) -> str:
        """移除状态效果"""
        for c in self.combatants:
            if c.name.lower() == target_name.lower():
                if condition in c.conditions:
                    c.conditions.remove(condition)
                return f"{c.name} 解除状态: {condition}"
        return f"找不到目标: {target_name}"

    def end_combat(self):
        """结束战斗"""
        self.is_active = False

    def check_combat_over(self) -> Optional[str]:
        """检查战斗是否结束"""
        players_alive = any(c.is_alive and c.is_player for c in self.combatants)
        monsters_alive = any(c.is_alive and not c.is_player for c in self.combatants)

        if not players_alive:
            self.end_combat()
            return "💀 全军覆没……冒险者们倒在了战场上。"
        if not monsters_alive:
            self.end_combat()
            return "🎉 战斗胜利！所有敌人已被击败。"
        return None

    def display_initiative_order(self) -> str:
        """显示先攻顺序"""
        lines = [f"⚔️ 【战斗 · 第 {self.round_number} 轮】\n", "先攻顺序："]
        for i, c in enumerate(self.combatants):
            marker = "▶️ " if i == self.current_turn else "  "
            hp_bar = f"HP: {c.current_hp}/{c.max_hp}"
            status = f" [{', '.join(c.conditions)}]" if c.conditions else ""
            alive_mark = "" if c.is_alive else " 💀"
            role = "👤" if c.is_player else "👹"

            lines.append(f"{marker}{role} {c.name} (先攻 {c.initiative}) | {hp_bar}{status}{alive_mark}")

        return "\n".join(lines)

    def display_turn_prompt(self) -> str:
        """显示当前回合提示"""
        current = self.get_current_combatant()
        if not current:
            return "战斗已结束"

        conditions_str = f"\n  状态: {', '.join(current.conditions)}" if current.conditions else ""

        if current.is_player:
            return (
                f"\n⚔️ 【第 {self.round_number} 轮】\n"
                f"轮到 {current.name} 行动！\n"
                f"  HP: {current.current_hp}/{current.max_hp} | AC: {current.ac}{conditions_str}\n"
                f"\n你要做什么？（攻击/施法/移动/冲刺/躲避/脱离/其他）"
            )
        else:
            return f"\n👹 {current.name} 的回合（GM 控制）"


# ========== 怪物模板 ==========
MONSTER_TEMPLATES = {
    "妖精": {"hp": 7, "ac": 15, "attack_bonus": 4, "damage_dice": "1d6", "damage_bonus": 2,
             "initiative_mod": 2, "xp": 50},
    "骷髅": {"hp": 13, "ac": 13, "attack_bonus": 4, "damage_dice": "1d6", "damage_bonus": 2,
             "initiative_mod": 2, "xp": 50},
    "僵尸": {"hp": 22, "ac": 8, "attack_bonus": 3, "damage_dice": "1d6", "damage_bonus": 1,
             "initiative_mod": -2, "xp": 50},
    "狼": {"hp": 11, "ac": 13, "attack_bonus": 4, "damage_dice": "2d4", "damage_bonus": 2,
           "initiative_mod": 1, "xp": 50},
    "强盗": {"hp": 11, "ac": 12, "attack_bonus": 3, "damage_dice": "1d6", "damage_bonus": 1,
             "initiative_mod": 1, "xp": 25},
    "强盗首领": {"hp": 65, "ac": 15, "attack_bonus": 5, "damage_dice": "1d8", "damage_bonus": 3,
                "initiative_mod": 2, "xp": 450},
    "巨蜘蛛": {"hp": 26, "ac": 14, "attack_bonus": 5, "damage_dice": "1d8", "damage_bonus": 3,
              "initiative_mod": 3, "xp": 200},
    "食尸鬼": {"hp": 22, "ac": 12, "attack_bonus": 4, "damage_dice": "2d6", "damage_bonus": 2,
              "initiative_mod": 2, "xp": 200},
    "地精": {"hp": 7, "ac": 15, "attack_bonus": 4, "damage_dice": "1d6", "damage_bonus": 2,
            "initiative_mod": 2, "xp": 50},
    "兽人": {"hp": 15, "ac": 13, "attack_bonus": 5, "damage_dice": "1d12", "damage_bonus": 3,
            "initiative_mod": 1, "xp": 100},
    "巨鼠": {"hp": 7, "ac": 12, "attack_bonus": 4, "damage_dice": "1d4", "damage_bonus": 2,
            "initiative_mod": 2, "xp": 25},
}


def spawn_monster(template_name: str, count: int = 1) -> List[dict]:
    """根据模板生成怪物参数列表"""
    template = MONSTER_TEMPLATES.get(template_name)
    if not template:
        return []

    monsters = []
    for i in range(count):
        name = f"{template_name}" if count == 1 else f"{template_name} {chr(65+i)}"
        monsters.append({
            "name": name,
            **{k: v for k, v in template.items() if k != "xp"}
        })
    return monsters


def list_monsters() -> str:
    """列出可用怪物模板"""
    lines = ["👹 可用怪物模板：\n"]
    for name, data in MONSTER_TEMPLATES.items():
        lines.append(f"  {name}: HP {data['hp']} | AC {data['ac']} | 攻击+{data['attack_bonus']} | {data['damage_dice']}+{data['damage_bonus']} | XP {data['xp']}")
    return "\n".join(lines)


# ========== CLI ==========
if __name__ == "__main__":
    print(list_monsters())
