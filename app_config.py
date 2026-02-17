"""
設定管理モジュール
アプリケーション設定とステータスを JSON で管理
"""

import json
import os
from typing import Dict, Optional


class AppConfig:
    """アプリケーション設定クラス"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = config_file
        self.co_point = 500  # CO 点数のデフォルト
        self.race_folder = "sample/race"
        self.settings_folder = "sample/setting"
        
        # 競技ステータス: status_map[ゼッケン][区間名] = "RIT" or "N.C." or "BLNK"
        self.status_map: Dict[int, Dict[str, str]] = {}
        
        # 最終結果ステータス: final_status[ゼッケン] = "RIT" or "N.C." or "BLNK"
        self.final_status: Dict[int, str] = {}
        
        # 初期化時にファイルから読み込み
        self.load()
    
    def load(self) -> bool:
        """設定ファイルを読み込む"""
        if not os.path.exists(self.config_file):
            # ファイルが存在しない場合はデフォルト値を使用
            return True
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.co_point = data.get('co_point', 500)
            self.race_folder = data.get('race_folder', 'sample/race')
            self.settings_folder = data.get('settings_folder', 'sample/setting')
            
            # ステータス情報の読み込み
            status_map_data = data.get('status_map', {})
            self.status_map = {}
            for zekken_str, sections in status_map_data.items():
                self.status_map[int(zekken_str)] = sections
            
            final_status_data = data.get('final_status', {})
            self.final_status = {}
            for zekken_str, status in final_status_data.items():
                self.final_status[int(zekken_str)] = status
            
            return True
        
        except Exception as e:
            print(f"設定ファイル読み込みエラー: {e}")
            return False
    
    def save(self) -> bool:
        """設定ファイルに保存"""
        try:
            # ステータス情報を辞書に変換（キーを文字列に）
            status_map_data = {}
            for zekken, sections in self.status_map.items():
                status_map_data[str(zekken)] = sections
            
            final_status_data = {}
            for zekken, status in self.final_status.items():
                final_status_data[str(zekken)] = status
            
            data = {
                'co_point': self.co_point,
                'race_folder': self.race_folder,
                'settings_folder': self.settings_folder,
                'status_map': status_map_data,
                'final_status': final_status_data
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            print(f"設定ファイル保存エラー: {e}")
            return False
    
    def set_section_status(self, zekken: int, section: str, status: str):
        """区間のステータスを設定"""
        if zekken not in self.status_map:
            self.status_map[zekken] = {}
        self.status_map[zekken][section] = status
    
    def get_section_status(self, zekken: int, section: str) -> Optional[str]:
        """区間のステータスを取得"""
        if zekken in self.status_map and section in self.status_map[zekken]:
            return self.status_map[zekken][section]
        return None
    
    def clear_section_status(self, zekken: int, section: str):
        """区間のステータスをクリア"""
        if zekken in self.status_map and section in self.status_map[zekken]:
            del self.status_map[zekken][section]
    
    def set_final_status(self, zekken: int, status: str):
        """最終結果ステータスを設定"""
        self.final_status[zekken] = status
    
    def get_final_status(self, zekken: int) -> Optional[str]:
        """最終結果ステータスを取得"""
        return self.final_status.get(zekken)
    
    def clear_final_status(self, zekken: int):
        """最終結果ステータスをクリア"""
        if zekken in self.final_status:
            del self.final_status[zekken]
