"""
設定ファイル読み込みモジュール
settings フォルダから entries, point, section ファイルを読み込む
"""

import os
import glob
import pandas as pd
from typing import Dict, Tuple, List


class SectionInfo:
    """セクション情報を保持するクラス"""
    def __init__(self, section: str, group=None, GROUP=None):
        self.section = section
        self.group = group
        self.GROUP = GROUP


class ConfigLoader:
    """設定ファイル読み込みクラス"""
    
    def __init__(self, settings_folder: str = "settings"):
        self.settings_folder = settings_folder
        self.entries_dict = {}
        self.point_dict = {}
        self.section_dict = {}
        self.section_df = None
        self._section_list_cache = None
    
    @property
    def section_list(self) -> List[SectionInfo]:
        """セクション情報のリストを取得"""
        if self._section_list_cache is not None:
            return self._section_list_cache
        
        if self.section_df is None:
            return []
        
        sections = []
        for _, row in self.section_df.iterrows():
            section_name = row.get('section', '')
            group = row.get('group', row.get('GROUP', None))
            sections.append(SectionInfo(
                section=section_name,
                group=group,
                GROUP=group
            ))
        
        self._section_list_cache = sections
        return sections
        
    def load_all(self) -> Tuple[bool, str]:
        """すべての設定ファイルを読み込む
        
        Returns:
            (成功: bool, エラーメッセージ: str)
        """
        # entries ファイル読み込み
        success, msg = self._load_entries()
        if not success:
            return False, msg
        
        # point ファイル読み込み
        success, msg = self._load_point()
        if not success:
            return False, msg
        
        # section ファイル読み込み
        success, msg = self._load_section()
        if not success:
            return False, msg
        
        return True, "設定ファイルを正常に読み込みました"
    
    def _find_file(self, pattern: str) -> Tuple[bool, str, str]:
        """指定されたパターンでファイルを検索
        
        Args:
            pattern: 検索パターン（例: "entries*.csv"）
        
        Returns:
            (成功: bool, ファイルパス: str, エラーメッセージ: str)
        """
        search_pattern = os.path.join(self.settings_folder, pattern)
        files = glob.glob(search_pattern)
        
        if len(files) == 0:
            return False, "", f"{pattern} ファイルが見つかりません"
        elif len(files) > 1:
            return False, "", f"{pattern} ファイルが複数存在します: {files}"
        
        return True, files[0], ""
    
    def _load_entries(self) -> Tuple[bool, str]:
        """entries ファイルを読み込む"""
        success, filepath, msg = self._find_file("entries*.csv")
        if not success:
            return False, msg
        
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            
            # 必須列チェック
            required_cols = ['No', 'DriverAge', 'CoDriverAge', '車製造年', '係数', '年齢係数']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return False, f"entries ファイルに必須列が不足しています: {missing_cols}"
            
            # ゼッケンごとに辞書作成
            for _, row in df.iterrows():
                zekken = row['No']
                if pd.isna(zekken) or zekken == 0:
                    continue
                
                self.entries_dict[int(zekken)] = {
                    'DriverName': row['DriverName'] if 'DriverName' in row and not pd.isna(row['DriverName']) else '',
                    'DriverAge': row['DriverAge'] if not pd.isna(row['DriverAge']) else 0,
                    'CoDriverName': row['CoDriverName'] if 'CoDriverName' in row and not pd.isna(row['CoDriverName']) else '',
                    'CoDriverAge': row['CoDriverAge'] if not pd.isna(row['CoDriverAge']) else 0,
                    'CarName': row['CarName'] if 'CarName' in row and not pd.isna(row['CarName']) else '',
                    'CarYear': row['車製造年'] if not pd.isna(row['車製造年']) else 0,
                    'CarClass': row['CarClass'] if 'CarClass' in row and not pd.isna(row['CarClass']) else '',
                    'Coef': row['係数'] if not pd.isna(row['係数']) else 1.0,
                    'AgeCoef': row['年齢係数'] if not pd.isna(row['年齢係数']) else 1.0
                }
            
            return True, ""
        
        except Exception as e:
            return False, f"entries ファイル読み込みエラー: {str(e)}"
    
    def _load_point(self) -> Tuple[bool, str]:
        """point ファイルを読み込む"""
        success, filepath, msg = self._find_file("point*.csv")
        if not success:
            return False, msg
        
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            
            # 必須列チェック
            required_cols = ['Order', 'Point']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return False, f"point ファイルに必須列が不足しています: {missing_cols}"
            
            # 順位 → 得点の辞書作成
            for _, row in df.iterrows():
                order = int(row['Order'])
                point = int(row['Point'])
                self.point_dict[order] = point
            
            return True, ""
        
        except Exception as e:
            return False, f"point ファイル読み込みエラー: {str(e)}"
    
    def _load_section(self) -> Tuple[bool, str]:
        """section ファイルを読み込む"""
        success, filepath, msg = self._find_file("section*.csv")
        if not success:
            return False, msg
        
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            
            # 必須列チェック
            required_cols = ['type', 'section', 'name', 'time', 'GROUP']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return False, f"section ファイルに必須列が不足しています: {missing_cols}"
            
            # DAY列が存在するか確認（オプション）
            self.has_day_column = 'DAY' in df.columns
            
            # DataFrame を保持（後で順序が必要）
            self.section_df = df
            
            # 区間名 → 設定タイムの辞書作成
            for _, row in df.iterrows():
                section_name = row['section']
                time_sec = int(row['time'])
                self.section_dict[section_name] = time_sec
            
            return True, ""
        
        except Exception as e:
            return False, f"section ファイル読み込みエラー: {str(e)}"
    
    def get_sections_by_group(self, group_num: int) -> list:
        """指定されたGROUP番号の区間リストを取得"""
        if self.section_df is None:
            return []
        
        group_df = self.section_df[self.section_df['GROUP'] == group_num]
        return group_df['section'].tolist()
    
    def get_sections_by_day(self, day_num: int) -> list:
        """指定されたDAY番号の区間リストを取得"""
        if self.section_df is None:
            return []
        
        if not hasattr(self, 'has_day_column') or not self.has_day_column:
            return []
        
        day_df = self.section_df[self.section_df['DAY'] == day_num]
        return day_df['section'].tolist()
    
    def get_max_day(self) -> int:
        """最大DAY番号を取得"""
        if self.section_df is None:
            return 0
        
        if not hasattr(self, 'has_day_column') or not self.has_day_column:
            return 0
        
        return int(self.section_df['DAY'].max())
    
    def get_section_order(self) -> list:
        """section ファイルの並び順で区間名リストを取得"""
        if self.section_df is None:
            return []
        return self.section_df['section'].tolist()
