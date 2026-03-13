"""
DnD存档处理器
直接集成到DnD游戏中，提供存档/读档功能
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class DnDSaveHandler:
    """DnD游戏存档处理器"""
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = base_dir
        self.char_dir = os.path.join(base_dir, "characters")
        self.save_dir = os.path.join(base_dir, "saves")
        
        # 确保目录存在
        os.makedirs(self.char_dir, exist_ok=True)
        os.makedirs(self.save_dir, exist_ok=True)
    
    def handle_save_command(self, command: str, game_state: Dict[str, Any], 
                           user_id: str = None, session_id: str = None) -> str:
        """处理存档相关命令"""
        command = command.lower().strip()
        
        if command in ["存档", "save"]:
            return self.save_game(game_state, session_id)
        
        elif command in ["读档", "load"]:
            return self.load_game(session_id)
        
        elif command in ["存档列表", "list saves"]:
            return self.list_saves()
        
        elif command in ["角色列表", "list characters"]:
            return self.list_characters()
        
        elif command in ["自动存档", "autosave"]:
            return "自动存档功能已启用（在关键节点自动保存）"
        
        elif command in ["删除存档", "delete save"]:
            return self.delete_save(session_id)
        
        elif command in ["删除角色", "delete character"] and user_id:
            return self.delete_character(user_id)
        
        else:
            return "未知的存档命令。可用命令：存档, 读档, 存档列表, 角色列表"
    
    def save_game(self, game_state: Dict[str, Any], session_id: str) -> str:
        """保存游戏进度"""
        if not session_id:
            return "错误：需要会话ID来保存游戏"
        
        filename = f"game_{session_id}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        # 添加元数据
        game_state["_metadata"] = {
            "saved_at": datetime.now().isoformat(),
            "session_id": session_id,
            "version": "1.0",
            "type": "game_save"
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(game_state, f, ensure_ascii=False, indent=2)
            
            # 创建备份（保留最近3个存档）
            self._create_backup(filepath)
            
            return f"✅ 游戏进度已保存到: {filename}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        except Exception as e:
            return f"❌ 保存失败: {str(e)}"
    
    def load_game(self, session_id: str) -> str:
        """加载游戏进度"""
        if not session_id:
            return "错误：需要会话ID来加载游戏"
        
        filename = f"game_{session_id}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        if not os.path.exists(filepath):
            # 尝试查找最新存档
            saves = self._find_latest_save()
            if saves:
                latest = saves[0]
                return f"未找到指定存档。最近存档: {latest['file']} ({latest['saved_at']})"
            return "❌ 未找到任何存档文件"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            meta = data.get("_metadata", {})
            saved_time = meta.get("saved_at", "未知时间")
            
            # 尝试解析时间
            try:
                dt = datetime.fromisoformat(saved_time.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = saved_time
            
            return f"✅ 找到存档: {filename}\n保存时间: {time_str}\n说'确认读档'加载此进度"
        
        except Exception as e:
            return f"❌ 读取存档失败: {str(e)}"
    
    def list_saves(self) -> str:
        """列出所有存档"""
        saves = self._find_latest_save(limit=10)
        
        if not saves:
            return "📭 暂无存档文件"
        
        result = "📁 可用存档:\n"
        for i, save in enumerate(saves, 1):
            result += f"{i}. {save['file']} - {save['saved_at']}\n"
        
        result += f"\n共 {len(saves)} 个存档"
        return result
    
    def list_characters(self) -> str:
        """列出所有角色"""
        chars = []
        if os.path.exists(self.char_dir):
            for file in os.listdir(self.char_dir):
                if file.endswith('.json'):
                    filepath = os.path.join(self.char_dir, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            char_data = data.get("character", {})
                            meta = data.get("_metadata", {})
                            
                            # 尝试解析时间
                            saved_time = meta.get("saved_at", "未知")
                            try:
                                dt = datetime.fromisoformat(saved_time.replace('Z', '+00:00'))
                                time_str = dt.strftime('%m-%d %H:%M')
                            except:
                                time_str = saved_time[:16]
                            
                            chars.append({
                                "name": char_data.get("name", "未知"),
                                "class": char_data.get("class", "未知"),
                                "level": char_data.get("level", 1),
                                "file": file,
                                "time": time_str,
                                "user": meta.get("user_id", "未知")
                            })
                    except:
                        chars.append({"name": "损坏文件", "file": file})
        
        if not chars:
            return "📭 暂无角色存档"
        
        result = "👤 角色存档列表:\n"
        for i, char in enumerate(chars, 1):
            result += f"{i}. {char['name']} - {char['class']} Lv.{char['level']} ({char['time']})\n"
        
        return result
    
    def delete_save(self, session_id: str) -> str:
        """删除存档"""
        if not session_id:
            return "错误：需要会话ID"
        
        filename = f"game_{session_id}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return f"✅ 已删除存档: {filename}"
        else:
            return f"❌ 未找到存档: {filename}"
    
    def delete_character(self, user_id: str) -> str:
        """删除角色"""
        filename = f"char_{user_id}.json"
        filepath = os.path.join(self.char_dir, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return f"✅ 已删除角色存档: {filename}"
        else:
            return f"❌ 未找到角色存档: {filename}"
    
    def _find_latest_save(self, limit: int = 5) -> list:
        """查找最新的存档文件"""
        saves = []
        if os.path.exists(self.save_dir):
            for file in os.listdir(self.save_dir):
                if file.endswith('.json'):
                    filepath = os.path.join(self.save_dir, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            meta = data.get("_metadata", {})
                            
                            # 获取保存时间
                            saved_time = meta.get("saved_at", "")
                            try:
                                dt = datetime.fromisoformat(saved_time.replace('Z', '+00:00'))
                                timestamp = dt.timestamp()
                            except:
                                timestamp = os.path.getmtime(filepath)
                                dt = datetime.fromtimestamp(timestamp)
                            
                            saves.append({
                                "file": file,
                                "path": filepath,
                                "saved_at": dt.strftime('%Y-%m-%d %H:%M:%S'),
                                "timestamp": timestamp,
                                "data": data
                            })
                    except:
                        # 如果JSON解析失败，使用文件修改时间
                        timestamp = os.path.getmtime(filepath)
                        dt = datetime.fromtimestamp(timestamp)
                        saves.append({
                            "file": file,
                            "path": filepath,
                            "saved_at": dt.strftime('%Y-%m-%d %H:%M:%S'),
                            "timestamp": timestamp,
                            "data": None
                        })
        
        # 按时间排序（最新的在前）
        saves.sort(key=lambda x: x["timestamp"], reverse=True)
        return saves[:limit]
    
    def _create_backup(self, original_path: str, max_backups: int = 3):
        """创建备份文件"""
        if not os.path.exists(original_path):
            return
        
        base_name = os.path.basename(original_path)
        name, ext = os.path.splitext(base_name)
        backup_dir = os.path.join(self.save_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        # 创建带时间戳的备份
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}{ext}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        import shutil
        shutil.copy2(original_path, backup_path)
        
        # 清理旧备份
        self._cleanup_old_backups(backup_dir, max_backups)
    
    def _cleanup_old_backups(self, backup_dir: str, max_backups: int):
        """清理旧的备份文件"""
        if not os.path.exists(backup_dir):
            return
        
        backups = []
        for file in os.listdir(backup_dir):
            if file.endswith('.json'):
                filepath = os.path.join(backup_dir, file)
                backups.append({
                    "path": filepath,
                    "mtime": os.path.getmtime(filepath)
                })
        
        if len(backups) > max_backups:
            # 按修改时间排序，删除最旧的
            backups.sort(key=lambda x: x["mtime"])
            for i in range(len(backups) - max_backups):
                try:
                    os.remove(backups[i]["path"])
                except:
                    pass


# ========== 使用示例 ==========

def example_usage():
    """使用示例"""
    print("=== DnD存档处理器示例 ===\n")
    
    # 初始化处理器
    handler = DnDSaveHandler()
    
    # 示例游戏状态
    game_state = {
        "campaign": "破碗亭之谜",
        "location": "破碗亭酒馆",
        "players": [
            {"name": "张顺飞", "class": "战士", "hp": 12},
            {"name": "夜鹰", "class": "法师", "hp": 7}
        ],
        "npcs": {
            "格里姆": {"status": "alive", "location": "吧台"}
        },
        "events": ["游戏开始", "进入酒馆", "与格里姆对话"]
    }
    
    # 测试保存
    print("1. 测试保存游戏:")
    result = handler.handle_save_command("存档", game_state, session_id="test_session_001")
    print(f"   {result}\n")
    
    # 测试列表
    print("2. 测试存档列表:")
    result = handler.handle_save_command("存档列表", game_state)
    print(f"   {result}\n")
    
    # 测试读档
    print("3. 测试读档:")
    result = handler.handle_save_command("读档", game_state, session_id="test_session_001")
    print(f"   {result}\n")
    
    # 测试角色列表（需要先创建角色文件）
    print("4. 测试角色列表:")
    result = handler.handle_save_command("角色列表", game_state)
    print(f"   {result}\n")
    
    print("=== 示例完成 ===")


if __name__ == "__main__":
    example_usage()