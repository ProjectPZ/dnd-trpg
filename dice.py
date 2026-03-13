"""
DnD 骰子引擎
支持标准骰子表达式：XdY+Z、优势/劣势、多次投掷
"""

import random
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class DiceResult:
    """单次掷骰结果"""
    expression: str          # 原始表达式
    rolls: List[int]         # 每个骰子的结果
    modifier: int            # 修正值
    total: int               # 总计
    dropped: List[int]       # 被丢弃的骰子（如 4d6 去最低）
    critical: bool           # 是否暴击（自然 20）
    fumble: bool             # 是否大失败（自然 1）
    advantage: bool          # 优势
    disadvantage: bool       # 劣势

    def display(self) -> str:
        """格式化显示结果"""
        parts = []

        if self.advantage:
            parts.append("🎯 [优势]")
        elif self.disadvantage:
            parts.append("💀 [劣势]")

        dice_str = ", ".join(str(r) for r in self.rolls)
        if self.dropped:
            dropped_str = ", ".join(f"~~{r}~~" for r in self.dropped)
            dice_str = f"{dice_str} (弃: {dropped_str})"

        parts.append(f"🎲 {self.expression} → [{dice_str}]")

        if self.modifier != 0:
            sign = "+" if self.modifier > 0 else ""
            parts.append(f"{sign}{self.modifier}")

        parts.append(f"= **{self.total}**")

        if self.critical:
            parts.append("💥 暴击！")
        elif self.fumble:
            parts.append("😱 大失败！")

        return " ".join(parts)


def parse_dice_expression(expr: str) -> Tuple[int, int, int]:
    """
    解析骰子表达式 XdY+Z
    返回 (数量, 面数, 修正值)
    """
    expr = expr.strip().lower().replace(" ", "")

    # 匹配 XdY+Z 或 XdY-Z 或 dY 或 XdY
    pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, expr)

    if not match:
        raise ValueError(f"无法解析骰子表达式: {expr}")

    num = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if num < 1 or num > 100:
        raise ValueError("骰子数量必须在 1~100 之间")
    if sides < 2 or sides > 100:
        raise ValueError("骰子面数必须在 2~100 之间")

    return num, sides, modifier


def roll(expression: str, advantage: bool = False, disadvantage: bool = False) -> DiceResult:
    """
    掷骰子

    Args:
        expression: 骰子表达式，如 "1d20+5", "2d6", "4d6kh3"
        advantage: 优势（掷两次取高）
        disadvantage: 劣势（掷两次取低）
    """
    num, sides, modifier = parse_dice_expression(expression)
    dropped = []

    if advantage and num == 1 and sides == 20:
        r1 = random.randint(1, 20)
        r2 = random.randint(1, 20)
        chosen = max(r1, r2)
        dropped = [min(r1, r2)]
        rolls = [chosen]
    elif disadvantage and num == 1 and sides == 20:
        r1 = random.randint(1, 20)
        r2 = random.randint(1, 20)
        chosen = min(r1, r2)
        dropped = [max(r1, r2)]
        rolls = [chosen]
    else:
        rolls = [random.randint(1, sides) for _ in range(num)]

    total = sum(rolls) + modifier

    # 检测暴击和大失败（仅 1d20）
    critical = (num == 1 and sides == 20 and rolls[0] == 20)
    fumble = (num == 1 and sides == 20 and rolls[0] == 1)

    return DiceResult(
        expression=expression,
        rolls=rolls,
        modifier=modifier,
        total=total,
        dropped=dropped,
        critical=critical,
        fumble=fumble,
        advantage=advantage,
        disadvantage=disadvantage
    )


def roll_ability_scores() -> List[dict]:
    """
    掷属性值：4d6 去掉最低，共 6 组
    返回每组的明细和总值
    """
    results = []
    for i in range(6):
        dice = sorted([random.randint(1, 6) for _ in range(4)], reverse=True)
        kept = dice[:3]
        dropped = dice[3:]
        total = sum(kept)
        results.append({
            "all_dice": dice,
            "kept": kept,
            "dropped": dropped[0],
            "total": total
        })
    return results


def roll_initiative(dex_mod: int) -> DiceResult:
    """掷先攻"""
    expr = f"1d20+{dex_mod}" if dex_mod >= 0 else f"1d20{dex_mod}"
    return roll(expr)


def format_ability_scores(scores: List[dict]) -> str:
    """格式化属性掷骰结果"""
    lines = ["🎲 属性掷骰结果（4d6 去最低）：", ""]
    for i, s in enumerate(scores, 1):
        dice_str = ", ".join(str(d) for d in s["kept"])
        lines.append(f"  第 {i} 组: [{dice_str}] (弃 {s['dropped']}) = **{s['total']}**")

    totals = sorted([s["total"] for s in scores], reverse=True)
    lines.append(f"\n  属性值: {totals}")
    lines.append("  请将这些数值分配到 STR/DEX/CON/INT/WIS/CHA")
    return "\n".join(lines)


# ========== 指令解析 ==========

DICE_PATTERN = re.compile(
    r"(?:掷骰|roll|骰子|投骰|丢骰子)\s*(\d*d\d+(?:[+-]\d+)?)",
    re.IGNORECASE
)

ADVANTAGE_KEYWORDS = ["优势", "advantage", "adv"]
DISADVANTAGE_KEYWORDS = ["劣势", "disadvantage", "dis", "disadv"]


def parse_roll_command(message: str) -> Optional[DiceResult]:
    """
    从消息中解析掷骰指令
    返回 DiceResult 或 None（如果不是掷骰指令）
    """
    match = DICE_PATTERN.search(message)
    if not match:
        return None

    expr = match.group(1)
    msg_lower = message.lower()

    adv = any(kw in msg_lower for kw in ADVANTAGE_KEYWORDS)
    dis = any(kw in msg_lower for kw in DISADVANTAGE_KEYWORDS)

    if adv and dis:
        adv = dis = False  # 优劣势抵消

    try:
        return roll(expr, advantage=adv, disadvantage=dis)
    except ValueError:
        return None


# ========== CLI ==========
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        expr = sys.argv[1]
        result = roll(expr)
        print(result.display())
    else:
        print("DnD 骰子引擎")
        print("用法: python dice.py <表达式>")
        print("示例: python dice.py 1d20+5")
        print()

        # 演示
        print("=== 演示 ===")
        for expr in ["1d20", "2d6+3", "1d20+5", "4d6", "1d12", "1d100"]:
            r = roll(expr)
            print(f"  {r.display()}")

        print("\n=== 属性掷骰 ===")
        scores = roll_ability_scores()
        print(format_ability_scores(scores))
