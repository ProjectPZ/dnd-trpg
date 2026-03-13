"""
DnD 5e 角色管理
角色创建、存档、加载、属性计算
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path


# ========== 种族数据 ==========
RACES = {
    "人类": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1, "speed": 30,
             "traits": ["额外语言"], "desc": "全属性+1，适应力强"},
    "高等精灵": {"dex": 2, "int": 1, "speed": 30,
                "traits": ["黑暗视觉", "精灵血统", "恍惚(不需睡眠)", "额外法术戏法"],
                "desc": "DEX+2 INT+1，擅长魔法"},
    "木精灵": {"dex": 2, "wis": 1, "speed": 35,
              "traits": ["黑暗视觉", "精灵血统", "恍惚", "自然隐匿"],
              "desc": "DEX+2 WIS+1，移动速度快"},
    "丘陵矮人": {"con": 2, "wis": 1, "speed": 25,
               "traits": ["黑暗视觉", "矮人韧性", "矮人战斗训练", "额外HP+1/级"],
               "desc": "CON+2 WIS+1，生命力顽强"},
    "山丘矮人": {"con": 2, "str": 2, "speed": 25,
               "traits": ["黑暗视觉", "矮人韧性", "矮人战斗训练", "中甲熟练"],
               "desc": "CON+2 STR+2，天生战士"},
    "轻足半身人": {"dex": 2, "cha": 1, "speed": 25,
                 "traits": ["幸运(1可重投)", "勇敢", "半身人灵活", "天生隐匿"],
                 "desc": "DEX+2 CHA+1，灵巧幸运"},
    "半精灵": {"cha": 2, "speed": 30,
              "traits": ["黑暗视觉", "精灵血统", "恍惚", "额外2项属性+1", "额外2项技能熟练"],
              "desc": "CHA+2 任选两项+1，社交达人"},
    "半兽人": {"str": 2, "con": 1, "speed": 30,
              "traits": ["黑暗视觉", "威吓熟练", "坚韧不屈(1次/长休HP降0时变1)", "野蛮攻击"],
              "desc": "STR+2 CON+1，凶猛持久"},
    "提夫林": {"cha": 2, "int": 1, "speed": 30,
              "traits": ["黑暗视觉", "火焰抗性", "地狱传承(奇术/灼热射线)"],
              "desc": "CHA+2 INT+1，地狱血脉"},
    "龙裔": {"str": 2, "cha": 1, "speed": 30,
            "traits": ["龙族血统(选择龙色)", "喷吐武器", "伤害抗性"],
            "desc": "STR+2 CHA+1，龙之力量"},
}

# ========== 职业数据 ==========
CLASSES = {
    "战士": {
        "hit_die": 10, "primary": "STR/DEX",
        "saving_throws": ["str", "con"],
        "armor": "全部盔甲和盾牌",
        "weapons": "简单武器和军用武器",
        "skills_choose": 2,
        "skills_from": ["杂技", "驯兽", "运动", "历史", "洞察", "威吓", "感知", "生存"],
        "features": {"1": ["战斗风格", "第二风(附赠行动恢复1d10+等级HP)"],
                     "2": ["行动如涌(额外行动1次/短休)"]},
        "desc": "近战专家，高生存力"
    },
    "法师": {
        "hit_die": 6, "primary": "INT",
        "saving_throws": ["int", "wis"],
        "armor": "无",
        "weapons": "匕首、飞镖、投石索、手杖、轻弩",
        "skills_choose": 2,
        "skills_from": ["奥秘", "历史", "洞察", "调查", "医药", "宗教"],
        "features": {"1": ["施法(INT)", "奥术恢复(短休恢复法术位)"]},
        "spellcasting": {"ability": "int", "cantrips": 3, "slots": {1: 2}},
        "desc": "强大的奥术施法者"
    },
    "游荡者": {
        "hit_die": 8, "primary": "DEX",
        "saving_throws": ["dex", "int"],
        "armor": "轻甲",
        "weapons": "简单武器、手弩、长剑、细剑、短剑",
        "skills_choose": 4,
        "skills_from": ["杂技", "运动", "欺瞒", "洞察", "威吓", "调查", "感知", "表演", "游说", "巧手", "隐匿"],
        "features": {"1": ["偷袭(1d6额外伤害)", "盗贼暗语"],
                     "2": ["狡猾行动(附赠行动冲刺/脱离/躲藏)"]},
        "desc": "灵巧狡诈，偷袭致命"
    },
    "牧师": {
        "hit_die": 8, "primary": "WIS",
        "saving_throws": ["wis", "cha"],
        "armor": "轻甲、中甲、盾牌",
        "weapons": "简单武器",
        "skills_choose": 2,
        "skills_from": ["历史", "洞察", "医药", "游说", "宗教"],
        "features": {"1": ["施法(WIS)", "神圣领域(选择)"]},
        "spellcasting": {"ability": "wis", "cantrips": 3, "slots": {1: 2}},
        "desc": "神圣治疗和支援"
    },
    "游侠": {
        "hit_die": 10, "primary": "DEX/WIS",
        "saving_throws": ["str", "dex"],
        "armor": "轻甲、中甲、盾牌",
        "weapons": "简单武器和军用武器",
        "skills_choose": 3,
        "skills_from": ["驯兽", "运动", "洞察", "调查", "自然", "感知", "隐匿", "生存"],
        "features": {"1": ["宿敌(选择)", "自然探索者(选择地形)"]},
        "desc": "荒野猎人和追踪者"
    },
    "野蛮人": {
        "hit_die": 12, "primary": "STR",
        "saving_throws": ["str", "con"],
        "armor": "轻甲、中甲、盾牌",
        "weapons": "简单武器和军用武器",
        "skills_choose": 2,
        "skills_from": ["驯兽", "运动", "威吓", "自然", "感知", "生存"],
        "features": {"1": ["狂暴(附赠行动，+2近战伤害，抗性)", "无甲防御(AC=10+DEX+CON)"]},
        "desc": "狂暴战士，极高生命值"
    },
    "吟游诗人": {
        "hit_die": 8, "primary": "CHA",
        "saving_throws": ["dex", "cha"],
        "armor": "轻甲",
        "weapons": "简单武器、手弩、长剑、细剑、短剑",
        "skills_choose": 3,
        "skills_from": ["任意"],
        "features": {"1": ["施法(CHA)", "鼓舞(CHA次/长休，1d6)"]},
        "spellcasting": {"ability": "cha", "cantrips": 2, "slots": {1: 2}},
        "desc": "万能辅助，社交之王"
    },
    "圣武士": {
        "hit_die": 10, "primary": "STR/CHA",
        "saving_throws": ["wis", "cha"],
        "armor": "全部盔甲和盾牌",
        "weapons": "简单武器和军用武器",
        "skills_choose": 2,
        "skills_from": ["运动", "洞察", "威吓", "医药", "游说", "宗教"],
        "features": {"1": ["神圣感知", "圣疗术(CHA×5 HP池)"]},
        "desc": "神圣战士，攻守兼备"
    },
    "术士": {
        "hit_die": 6, "primary": "CHA",
        "saving_throws": ["con", "cha"],
        "armor": "无",
        "weapons": "匕首、飞镖、投石索、手杖、轻弩",
        "skills_choose": 2,
        "skills_from": ["奥秘", "欺瞒", "洞察", "威吓", "游说", "宗教"],
        "features": {"1": ["施法(CHA)", "术法起源(选择)", "2个魔力点"]},
        "spellcasting": {"ability": "cha", "cantrips": 4, "slots": {1: 2}},
        "desc": "天生魔法，灵活施法"
    },
    "邪术师": {
        "hit_die": 8, "primary": "CHA",
        "saving_throws": ["wis", "cha"],
        "armor": "轻甲",
        "weapons": "简单武器",
        "skills_choose": 2,
        "skills_from": ["奥秘", "欺瞒", "历史", "威吓", "调查", "自然", "宗教"],
        "features": {"1": ["施法(CHA)", "异界宗主(选择)", "契约魔法(短休恢复)"]},
        "spellcasting": {"ability": "cha", "cantrips": 2, "slots": {1: 1}},
        "desc": "契约法师，短休回复法术位"
    },
    "德鲁伊": {
        "hit_die": 8, "primary": "WIS",
        "saving_throws": ["int", "wis"],
        "armor": "轻甲、中甲、盾牌(非金属)",
        "weapons": "木棒、匕首、飞镖、标枪、硬头锤、长棍、弯刀、镰刀、投石索、矛",
        "skills_choose": 2,
        "skills_from": ["奥秘", "驯兽", "洞察", "医药", "自然", "感知", "宗教", "生存"],
        "features": {"1": ["施法(WIS)", "德鲁伊语"]},
        "spellcasting": {"ability": "wis", "cantrips": 2, "slots": {1: 2}},
        "desc": "自然法师，可变身野兽"
    },
    "武僧": {
        "hit_die": 8, "primary": "DEX/WIS",
        "saving_throws": ["str", "dex"],
        "armor": "无",
        "weapons": "简单武器、短剑",
        "skills_choose": 2,
        "skills_from": ["杂技", "运动", "历史", "洞察", "宗教", "隐匿"],
        "features": {"1": ["无甲防御(AC=10+DEX+WIS)", "武术(1d4武僧武器)"]},
        "desc": "近战格斗家，高机动"
    },
}

# ========== 属性调整值计算 ==========
def ability_modifier(score: int) -> int:
    return (score - 10) // 2

def mod_str(mod: int) -> str:
    return f"+{mod}" if mod >= 0 else str(mod)


# ========== 角色数据类 ==========
@dataclass
class Character:
    # 基本信息
    name: str = ""
    player_id: str = ""           # Telegram user ID
    race: str = ""
    char_class: str = ""
    level: int = 1
    background: str = ""
    xp: int = 0

    # 六项属性
    str_score: int = 10
    dex_score: int = 10
    con_score: int = 10
    int_score: int = 10
    wis_score: int = 10
    cha_score: int = 10

    # 战斗数据
    max_hp: int = 0
    current_hp: int = 0
    temp_hp: int = 0
    ac: int = 10
    speed: int = 30
    hit_dice_remaining: int = 0

    # 熟练
    proficiency_bonus: int = 2
    skill_proficiencies: List[str] = field(default_factory=list)
    saving_throw_proficiencies: List[str] = field(default_factory=list)

    # 装备和物品
    equipment: List[str] = field(default_factory=list)
    gold: float = 0

    # 法术（如果有）
    spell_slots: Dict[int, int] = field(default_factory=dict)
    spell_slots_used: Dict[int, int] = field(default_factory=dict)
    known_spells: List[str] = field(default_factory=list)
    cantrips: List[str] = field(default_factory=list)

    # 特性
    features: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)

    # 状态
    conditions: List[str] = field(default_factory=list)
    death_saves_success: int = 0
    death_saves_fail: int = 0

    @property
    def str_mod(self): return ability_modifier(self.str_score)
    @property
    def dex_mod(self): return ability_modifier(self.dex_score)
    @property
    def con_mod(self): return ability_modifier(self.con_score)
    @property
    def int_mod(self): return ability_modifier(self.int_score)
    @property
    def wis_mod(self): return ability_modifier(self.wis_score)
    @property
    def cha_mod(self): return ability_modifier(self.cha_score)

    @property
    def initiative(self): return self.dex_mod

    def display_card(self) -> str:
        xp_table = {1:0, 2:300, 3:900, 4:2700, 5:6500, 6:14000, 7:23000, 8:34000, 9:48000, 10:64000}
        next_xp = xp_table.get(self.level + 1, "MAX")

        skills_str = ", ".join(self.skill_proficiencies) if self.skill_proficiencies else "无"
        equip_str = ", ".join(self.equipment) if self.equipment else "无"
        conditions_str = ", ".join(self.conditions) if self.conditions else "正常"

        return (
            f"═══════════════════════════════\n"
            f"  {self.name} | {self.race} {self.char_class} Lv.{self.level}\n"
            f"═══════════════════════════════\n"
            f"  HP: {self.current_hp}/{self.max_hp} | AC: {self.ac} | 状态: {conditions_str}\n"
            f"  先攻修正: {mod_str(self.initiative)} | 速度: {self.speed}ft\n"
            f"───────────────────────────────\n"
            f"  力量 STR: {self.str_score} ({mod_str(self.str_mod)})\n"
            f"  敏捷 DEX: {self.dex_score} ({mod_str(self.dex_mod)})\n"
            f"  体质 CON: {self.con_score} ({mod_str(self.con_mod)})\n"
            f"  智力 INT: {self.int_score} ({mod_str(self.int_mod)})\n"
            f"  感知 WIS: {self.wis_score} ({mod_str(self.wis_mod)})\n"
            f"  魅力 CHA: {self.cha_score} ({mod_str(self.cha_mod)})\n"
            f"───────────────────────────────\n"
            f"  熟练加值: +{self.proficiency_bonus}\n"
            f"  熟练技能: {skills_str}\n"
            f"───────────────────────────────\n"
            f"  装备: {equip_str}\n"
            f"  金币: {self.gold} gp\n"
            f"  经验: {self.xp}/{next_xp}\n"
            f"═══════════════════════════════"
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ========== 角色存档管理 ==========

def save_character(char: Character, char_dir: str = "characters"):
    """保存角色到 JSON 文件"""
    Path(char_dir).mkdir(parents=True, exist_ok=True)
    filename = f"{char.player_id}_{char.name}.json"
    filepath = Path(char_dir) / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(char.to_dict(), f, ensure_ascii=False, indent=2)
    return filepath


def load_character(player_id: str, char_dir: str = "characters") -> Optional[Character]:
    """加载玩家的角色"""
    char_path = Path(char_dir)
    if not char_path.exists():
        return None

    for f in char_path.glob(f"{player_id}_*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        return Character.from_dict(data)
    return None


def load_all_characters(char_dir: str = "characters") -> List[Character]:
    """加载所有角色"""
    chars = []
    char_path = Path(char_dir)
    if not char_path.exists():
        return chars

    for f in char_path.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        chars.append(Character.from_dict(data))
    return chars


def delete_character(player_id: str, char_dir: str = "characters") -> bool:
    """删除玩家的角色"""
    char_path = Path(char_dir)
    for f in char_path.glob(f"{player_id}_*.json"):
        os.remove(f)
        return True
    return False


# ========== 角色创建辅助 ==========

def calculate_hp(char_class: str, con_mod: int, level: int = 1) -> int:
    """计算 HP"""
    cls = CLASSES.get(char_class)
    if not cls:
        return 10
    hit_die = cls["hit_die"]
    # 1 级取最大生命骰 + CON 调整值
    hp = hit_die + con_mod
    # 后续等级取平均值
    avg = (hit_die // 2) + 1
    hp += (level - 1) * (avg + con_mod)
    return max(hp, 1)


def calculate_ac(char: Character) -> int:
    """计算基础 AC（不含装备加成）"""
    # 野蛮人无甲防御
    if char.char_class == "野蛮人":
        return 10 + char.dex_mod + char.con_mod
    # 武僧无甲防御
    if char.char_class == "武僧":
        return 10 + char.dex_mod + char.wis_mod
    # 默认无甲
    return 10 + char.dex_mod


def list_races() -> str:
    """列出所有种族供选择"""
    lines = ["🧝 可选种族：\n"]
    for name, data in RACES.items():
        bonuses = []
        for attr in ["str", "dex", "con", "int", "wis", "cha"]:
            if attr in data and isinstance(data[attr], int):
                bonuses.append(f"{attr.upper()}+{data[attr]}")
        bonus_str = ", ".join(bonuses)
        lines.append(f"  {name} ({bonus_str}) {data['desc']}")
    return "\n".join(lines)


def list_classes() -> str:
    """列出所有职业供选择"""
    lines = ["⚔️ 可选职业：\n"]
    for name, data in CLASSES.items():
        lines.append(f"  {name} (d{data['hit_die']}) {data['desc']}")
    return "\n".join(lines)


# ========== CLI ==========
if __name__ == "__main__":
    print(list_races())
    print()
    print(list_classes())
