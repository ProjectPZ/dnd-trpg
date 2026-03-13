"""
DnD 战役模组解析器
支持从聊天框粘贴模组文本，自动识别并保存到 campaigns/ 目录
"""

import re
import os
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from pathlib import Path


@dataclass
class Chapter:
    """模组章节"""
    title: str = ""
    scenes: str = ""           # 场景描述
    npcs: str = ""             # NPC 信息
    encounters: str = ""       # 遭遇信息
    checks: str = ""           # 检定信息
    loot: str = ""             # 战利品
    raw_text: str = ""         # 原始文本


@dataclass
class Campaign:
    """战役模组"""
    id: str = ""
    name: str = ""
    campaign_type: str = ""
    player_count: str = ""
    background: str = ""
    opening: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    ending: str = ""
    source_file: str = ""
    raw_text: str = ""

    def to_dict(self):
        return asdict(self)


def _generate_id(name: str, text: str) -> str:
    """根据模组名和内容生成唯一 ID"""
    content = f"{name.strip()}|{text[:200].strip()}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]


def contains_campaign_pattern(text: str) -> bool:
    """
    快速检测文本是否包含模组特征。
    用于在聊天消息中判断用户是否在粘贴模组。

    判定条件：包含"模组名称"关键词
    """
    return bool(re.search(r"模组名称\s*[:：]", text))


def parse_campaign_text(raw_text: str, source_file: str = "") -> Optional[Campaign]:
    """
    从原始文本解析模组

    识别关键词：
    - 模组名称：xxx
    - 背景：xxx
    - 开场引导：xxx
    - 第X章：xxx（或用分隔线分章）
    - 结局
    """
    # 提取模组名称
    name_match = re.search(r"模组名称\s*[:：]\s*(.+?)(?:\n|$)", raw_text)
    if not name_match:
        return None

    name = name_match.group(1).strip()
    campaign_id = _generate_id(name, raw_text)

    # 提取类型和人数
    type_match = re.search(r"类型\s*[:：]\s*(.+?)(?:\n|$)", raw_text)
    count_match = re.search(r"建议人数\s*[:：]\s*(.+?)(?:\n|$)", raw_text)

    # 提取背景
    bg_match = re.search(r"背景\s*[:：]\s*\n?([\s\S]+?)(?=开场引导|第[一二三四五六七八九十\d]+章|═|$)", raw_text)

    # 提取开场引导
    opening_match = re.search(r"开场引导\s*[:：]\s*\n?([\s\S]+?)(?=第[一二三四五六七八九十\d]+章|═|$)", raw_text)

    # 提取章节（用分隔线或"第X章"切分）
    chapter_pattern = r"(?:═+\s*\n)?第[一二三四五六七八九十\d]+章\s*[:：]\s*(.+?)\n([\s\S]+?)(?=(?:═+\s*\n)?第[一二三四五六七八九十\d]+章|(?:═+\s*\n)?结局|$)"
    chapter_matches = re.finditer(chapter_pattern, raw_text)

    chapters = []
    for cm in chapter_matches:
        chapter = Chapter(
            title=cm.group(1).strip(),
            raw_text=cm.group(2).strip()
        )
        chapters.append(chapter)

    # 提取结局
    ending_match = re.search(r"(?:═+\s*\n)?结局\s*(?:═+\s*\n)?\s*([\s\S]+?)$", raw_text)

    campaign = Campaign(
        id=campaign_id,
        name=name,
        campaign_type=type_match.group(1).strip() if type_match else "",
        player_count=count_match.group(1).strip() if count_match else "",
        background=bg_match.group(1).strip() if bg_match else "",
        opening=opening_match.group(1).strip() if opening_match else "",
        chapters=chapters,
        ending=ending_match.group(1).strip() if ending_match else "",
        source_file=source_file,
        raw_text=raw_text
    )

    return campaign


def parse_campaign_file(filepath: str) -> Optional[Campaign]:
    """解析单个模组文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()
    return parse_campaign_text(raw_text, source_file=os.path.basename(filepath))


def load_all_campaigns(campaign_dir: str) -> List[Campaign]:
    """加载目录下所有模组"""
    campaigns = []
    campaign_path = Path(campaign_dir)
    if not campaign_path.exists():
        return campaigns

    for f in sorted(campaign_path.glob("*.txt")):
        try:
            c = parse_campaign_file(str(f))
            if c:
                campaigns.append(c)
        except Exception as e:
            print(f"[WARNING] 解析 {f.name} 时出错: {e}")

    # 也支持 .md 文件
    for f in sorted(campaign_path.glob("*.md")):
        try:
            c = parse_campaign_file(str(f))
            if c:
                campaigns.append(c)
        except Exception as e:
            print(f"[WARNING] 解析 {f.name} 时出错: {e}")

    return campaigns


def append_campaign(raw_text: str, campaign_dir: str) -> Optional[Campaign]:
    """
    将用户粘贴的模组文本保存到文件。

    流程：
    1. 解析文本，确认包含有效模组
    2. 与现有模组去重
    3. 以模组名为文件名保存
    4. 返回新增的模组
    """
    campaign = parse_campaign_text(raw_text)
    if not campaign:
        return None

    # 检查去重
    existing = load_all_campaigns(campaign_dir)
    existing_ids = {c.id for c in existing}

    if campaign.id in existing_ids:
        return None  # 重复

    # 生成文件名（用模组名，去掉特殊字符）
    safe_name = re.sub(r'[\\/:*?"<>|\s]', '_', campaign.name)
    filename = f"{safe_name}.txt"
    target_path = Path(campaign_dir) / filename
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果文件名已存在，加序号
    counter = 1
    while target_path.exists():
        filename = f"{safe_name}_{counter}.txt"
        target_path = Path(campaign_dir) / filename
        counter += 1

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(raw_text.strip())
        f.write("\n")

    campaign.source_file = filename
    return campaign


def list_campaigns(campaign_dir: str) -> str:
    """列出所有可用模组"""
    campaigns = load_all_campaigns(campaign_dir)
    if not campaigns:
        return "📜 题库为空，请添加模组到 campaigns/ 目录。"

    lines = ["📜 可用模组：\n"]
    for c in campaigns:
        chapter_count = len(c.chapters)
        type_str = f" ({c.campaign_type})" if c.campaign_type else ""
        player_str = f" | {c.player_count}" if c.player_count else ""
        lines.append(f"  📖 {c.name}{type_str}{player_str} | {chapter_count} 章")

    return "\n".join(lines)


# ========== CLI ==========
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python campaign_parser.py <campaigns_dir>")
        sys.exit(1)

    campaign_dir = sys.argv[1]
    campaigns = load_all_campaigns(campaign_dir)

    print(f"共加载 {len(campaigns)} 个模组：")
    for c in campaigns:
        print(f"  [{c.id}] {c.name} | {len(c.chapters)} 章")
        for ch in c.chapters:
            print(f"    - {ch.title}")
