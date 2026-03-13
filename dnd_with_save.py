"""
带存档功能的DnD游戏包装器
集成存档处理器，提供完整的存档/读档体验
"""

import os
import sys
from save_handler import DnDSaveHandler

class DnDGameWithSave:
    """带存档功能的DnD游戏"""
    
    def __init__(self):
        self.save_handler = DnDSaveHandler()
        self.game_active = False
        self.current_session = None
        self.game_state = {}
        
        print("🎲 DnD游戏已启动（带存档功能）")
        print("可用存档命令：存档, 读档, 存档列表, 角色列表, 自动存档\n")
    
    def process_command(self, command: str, user_id: str = None) -> str:
        """处理游戏命令"""
        command_lower = command.lower().strip()
        
        # 存档相关命令
        if command_lower in ["存档", "save", "读档", "load", "存档列表", "list saves", 
                           "角色列表", "list characters", "自动存档", "autosave",
                           "删除存档", "delete save", "删除角色", "delete character"]:
            return self.save_handler.handle_save_command(
                command_lower, self.game_state, user_id, self.current_session
            )
        
        # 游戏开始命令
        elif command_lower in ["开始跑团", "开团", "跑团", "dnd", "开始冒险"]:
            return self.start_game(user_id)
        
        # 角色创建命令
        elif command_lower.startswith("创建角色") or command_lower.startswith("建卡"):
            return self.create_character(command, user_id)
        
        # 游戏内命令
        elif self.game_active:
            return self.game_command(command, user_id)
        
        # 未知命令
        else:
            return "请说'开始跑团'开始游戏，或使用存档命令管理进度。"
    
    def start_game(self, user_id: str) -> str:
        """开始新游戏"""
        self.game_active = True
        self.current_session = f"session_{user_id}_{int(os.times()[4])}"
        
        # 初始化游戏状态
        self.game_state = {
            "campaign": "破碗亭之谜",
            "location": "法纳林镇入口",
            "players": [],
            "npcs": {},
            "events": ["游戏开始"],
            "combat": None,
            "timestamp": os.times()[4]
        }
        
        return (
            "🎲 欢迎来到《破碗亭之谜》D&D冒险！\n\n"
            "法纳林镇是一个宁静的边境小镇。最近，镇上唯一的酒馆'破碗亭'发生怪事：\n"
            "酒窖夜间有奇怪声响，酒桶神秘失踪，帮工小汤姆在调查时失踪。\n"
            "镇长悬赏50金币招募冒险者。\n\n"
            "💾 游戏已自动创建会话，可以说'存档'保存进度。\n"
            "👤 请先创建角色：说'创建角色 <名字> <职业>' 或 '建卡 <名字> <职业>'\n"
            "   可用职业：战士、法师、游荡者、牧师、游侠、术士"
        )
    
    def create_character(self, command: str, user_id: str) -> str:
        """创建角色"""
        if not self.game_active:
            return "请先开始游戏（说'开始跑团'）"
        
        parts = command.split()
        if len(parts) < 3:
            return "格式：创建角色 <名字> <职业>"
        
        name = parts[1]
        char_class = parts[2]
        
        # 验证职业
        valid_classes = ["战士", "法师", "游荡者", "牧师", "游侠", "术士"]
        if char_class not in valid_classes:
            return f"无效职业。可用职业：{', '.join(valid_classes)}"
        
        # 创建角色数据
        character = self._generate_character(name, char_class, user_id)
        
        # 添加到游戏状态
        if "players" not in self.game_state:
            self.game_state["players"] = []
        
        # 检查是否已有该用户的角色
        for i, player in enumerate(self.game_state["players"]):
            if player.get("user_id") == user_id:
                self.game_state["players"][i] = character
                break
        else:
            self.game_state["players"].append(character)
        
        # 保存角色到独立文件
        char_data = {
            "character": character,
            "_metadata": {
                "user_id": user_id,
                "created_at": os.times()[4],
                "game_session": self.current_session
            }
        }
        
        # 使用存档处理器保存角色
        char_file = f"char_{user_id}.json"
        char_path = os.path.join(self.save_handler.char_dir, char_file)
        
        import json
        with open(char_path, 'w', encoding='utf-8') as f:
            json.dump(char_data, f, ensure_ascii=False, indent=2)
        
        # 自动保存游戏进度
        self.save_handler.save_game(self.game_state, self.current_session)
        
        return (
            f"✅ 角色创建成功！\n\n"
            f"👤 {name} - {char_class} Lv.1\n"
            f"❤️ HP: {character['hp']} | 🛡️ AC: {character['ac']}\n"
            f"💪 属性: 力量{character['attributes']['str']} 敏捷{character['attributes']['dex']} "
            f"体质{character['attributes']['con']} 智力{character['attributes']['int']} "
            f"感知{character['attributes']['wis']} 魅力{character['attributes']['cha']}\n\n"
            f"💾 角色已保存，游戏进度已自动存档。\n"
            f"说'进入酒馆'开始冒险，或说'存档'手动保存。"
        )
    
    def _generate_character(self, name: str, char_class: str, user_id: str) -> dict:
        """生成角色数据"""
        # 基础属性（简化版）
        if char_class == "战士":
            attributes = {"str": 16, "dex": 14, "con": 15, "int": 10, "wis": 12, "cha": 8}
            hp = 12
            ac = 16
        elif char_class == "法师":
            attributes = {"str": 8, "dex": 15, "con": 13, "int": 16, "wis": 10, "cha": 12}
            hp = 7
            ac = 12
        elif char_class == "游荡者":
            attributes = {"str": 10, "dex": 16, "con": 14, "int": 12, "wis": 10, "cha": 13}
            hp = 9
            ac = 14
        else:  # 默认
            attributes = {"str": 12, "dex": 12, "con": 12, "int": 12, "wis": 12, "cha": 12}
            hp = 10
            ac = 13
        
        return {
            "name": name,
            "class": char_class,
            "level": 1,
            "hp": hp,
            "max_hp": hp,
            "ac": ac,
            "attributes": attributes,
            "user_id": user_id,
            "equipment": [],
            "gold": 10,
            "xp": 0
        }
    
    def game_command(self, command: str, user_id: str) -> str:
        """处理游戏内命令"""
        command_lower = command.lower().strip()
        
        if command_lower == "进入酒馆":
            return self.enter_tavern()
        
        elif command_lower == "查看状态":
            return self.check_status(user_id)
        
        elif command_lower == "队伍":
            return self.check_party()
        
        elif command_lower == "掷骰 1d20":
            import random
            roll = random.randint(1, 20)
            return f"🎲 掷骰 1d20 = {roll}"
        
        elif command_lower.startswith("掷骰"):
            # 简单的骰子解析
            try:
                parts = command_lower.split()
                dice = parts[1]  # 如 "1d20" 或 "2d6+3"
                return f"🎲 掷骰 {dice} = [模拟结果]"
            except:
                return "掷骰格式：掷骰 XdY 或 掷骰 XdY+Z"
        
        elif command_lower == "帮助":
            return self.show_help()
        
        else:
            return f"执行命令：{command}\n（这是模拟响应，完整DnD引擎需要更复杂的实现）"
    
    def enter_tavern(self) -> str:
        """进入酒馆场景"""
        self.game_state["location"] = "破碗亭酒馆"
        self.game_state["events"].append("进入酒馆")
        
        # 自动保存
        self.save_handler.save_game(self.game_state, self.current_session)
        
        return (
            "🏰 你推开破碗亭酒馆吱嘎作响的木门...\n\n"
            "酒馆内温暖而略显陈旧，墙上挂着几个缺了口的木碗作为装饰。\n"
            "午后的酒馆只有零星几个酒客，吧台后面站着一个40多岁、络腮胡的男人——格里姆。\n"
            "他看起来几天没睡好，眼圈发黑。\n\n"
            "格里姆看到冒险者，眼睛一亮：'你们来得正好！我这儿出大事了...'\n\n"
            "💬 你可以：\n"
            "1. 询问格里姆具体情况\n"
            "2. 直接要求查看酒窖\n"
            "3. 先观察酒馆环境\n"
            "4. 说'存档'保存进度\n"
            "5. 其他行动描述"
        )
    
    def check_status(self, user_id: str) -> str:
        """查看角色状态"""
        for player in self.game_state.get("players", []):
            if player.get("user_id") == user_id:
                return (
                    f"👤 {player['name']} - {player['class']} Lv.{player['level']}\n"
                    f"❤️ HP: {player['hp']}/{player['max_hp']} | 🛡️ AC: {player['ac']}\n"
                    f"💰 金币: {player['gold']}gp | 📈 经验: {player['xp']}\n"
                    f"📍 位置: {self.game_state.get('location', '未知')}"
                )
        return "未找到你的角色信息"
    
    def check_party(self) -> str:
        """查看队伍状态"""
        players = self.game_state.get("players", [])
        if not players:
            return "队伍中没有玩家"
        
        result = "👥 队伍成员：\n"
        for player in players:
            result += f"• {player['name']} - {player['class']} Lv.{player['level']} (❤️{player['hp']}/{player['max_hp']})\n"
        
        result += f"\n📍 当前位置：{self.game_state.get('location', '未知')}"
        return result
    
    def show_help(self) -> str:
        """显示帮助"""
        return (
            "🎲 DnD游戏帮助\n\n"
            "📋 游戏命令：\n"
            "• 开始跑团 - 开始新游戏\n"
            "• 创建角色 <名字> <职业> - 创建角色\n"
            "• 进入酒馆 - 进入第一个场景\n"
            "• 查看状态 - 查看自己角色\n"
            "• 队伍 - 查看全队状态\n"
            "• 掷骰 XdY - 掷骰子\n\n"
            "💾 存档命令：\n"
            "• 存档 - 保存游戏进度\n"
            "• 读档 - 加载最近存档\n"
            "• 存档列表 - 查看所有存档\n"
            "• 角色列表 - 查看角色存档\n"
            "• 自动存档 - 启用自动保存\n\n"
            "🎮 游戏内：用自然语言描述行动，DM会回应。"
        )


# ========== 交互式测试 ==========

def interactive_test():
    """交互式测试"""
    print("=== DnD游戏带存档功能 - 交互测试 ===\n")
    print("输入命令测试，输入'退出'结束测试\n")
    
    game = DnDGameWithSave()
    user_id = "test_user_001"
    
    while True:
        try:
            cmd = input("> ").strip()
            if cmd.lower() in ["退出", "exit", "quit"]:
                print("测试结束")
                break
            
            response = game.process_command(cmd, user_id)
            print(f"\n{response}\n")
            
        except (EOFError, KeyboardInterrupt):
            print("\n测试结束")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        interactive_test()
    else:
        print("DnD游戏带存档功能已就绪")
        print("使用方法：")
        print("1. 将此模块集成到DnD技能中")
        print("2. 或运行: python dnd_with_save.py test 进行交互测试")